---
id: T-136
phase: 1
title: apps/backend — GET /api/v1/predictions/route/{id}?horizon=year (долгосрочный прогноз через Monte Carlo)
priority: P1
effort: 4
unit: hours
rice:
  R: 4
  I: 2.0
  C: 0.6
  score: 1.2
depends_on: [T-036, T-134]
blocks: []
tags: [backend, api, predictions, horizon, year, monte-carlo, beneficiary, hackathon]
status: backlog
created: 2026-09-23
updated: 2026-09-25
assignee: "maxim"
---

# T-136: backend — endpoint /api/v1/predictions/route/{id}?horizon=year (Monte Carlo)

## Context

ТЗ §3.1.2 (третий обязательный горизонт):
> «Долгосрочный (1 год) — помесячный прогноз с учётом открытия новых маршрутов, изменения
>  городской инфраструктуры (мета-обучение для новых остановок).»

ТЗ §5 Этап 2:
> «Долгосрочный прогноз (Марковские цепи + мета-обучение)… Построить матрицы переходов
>  между районами (или остановками)… Реализовать мета-обучение для новых остановок.»

ТЗ §7.2 (метрика):
> «Для долгосрочного (1 год) RMSLE < 0.60.»

Текущее состояние:
- T-036 (Monte Carlo simulator) есть в `tickets/`, но **не реализован** (assignee пустой).
- `apps/backend/app/api/predictions.py` имеет только day-horizon.
- README.md обещает "три горизонта (день/месяц/год)" — 2 из 3 отсутствуют.

Этот тикет — **glue между T-036 (Monte Carlo как библиотека) и HTTP endpoint**.

## Acceptance Criteria

- [ ] Endpoint `GET /api/v1/predictions/route/{route_id}?horizon=year&n_scenarios=1000`
- [ ] Параметры: route_id (path), horizon=year, n_scenarios (default 1000, max 10000)
- [ ] Response: `YearlyPredictionsResponse` с scenarios (per-month: value_mean, value_p10, value_p90)
- [ ] При kind="montecarlo" — используем MC напрямую
- [ ] При kind in {baseline, xgboost} — обёртка с Gaussian noise
- [ ] При отсутствии активного артефакта — 503
- [ ] Валидация: n_scenarios <= 10000, latency < 5 сек
- [ ] make api-gen обновляет OpenAPI (тот же endpoint что в T-134, расширен)
- [ ] Unit-тесты: `apps/backend/tests/test_yearly_endpoint.py` (5+ кейсов)
- [ ] Backend latency logged: time.perf_counter()

## Technical Notes

Структура endpoint (расширение T-134):
```python
@router.get("/predictions/route/{route_id}", response_model=YearlyPredictionsResponse)
def get_yearly_predictions(
    route_id: int = Path(..., ge=1),
    horizon: Literal["day", "month", "year"] = Query("year"),
    n_scenarios: int = Query(1000, ge=1, le=10000),
    loader: ArtifactLoader = Depends(get_loader),
):
    if horizon == "year":
        mc = MonteCarloSimulator(predictor=loader.get_predictor(), n_scenarios=n_scenarios)
        scenarios = mc.simulate(route_id=route_id, horizon_months=12)
        return _summarize_scenarios(scenarios)
```

Зависимость: T-036 — `ml/transit_ai/montecarlo/simulator.py`.

Fallback (когда T-036 не готов):
```python
def _monte_carlo_fallback(predictor, route_id, n_scenarios):
    """Fallback когда T-036 MonteCarloSimulator не реализован."""
    import numpy as np
    base = predictor.predict(route_id, datetime(2026, 1, 1), datetime(2026, 12, 31))
    monthly_base = {}
    for point in base:
        key = (point.period_start.year, point.period_start.month)
        monthly_base[key] = monthly_base.get(key, 0.0) + point.value
    std = 0.15 * np.mean(list(monthly_base.values()))
    scenarios = {key: np.random.normal(mean, std, n_scenarios) for key, mean in monthly_base.items()}
    return scenarios
```

## Verification

```bash
# 1. Type-check
uv run mypy apps/backend/app/

# 2. Tests
uv run pytest apps/backend/tests/test_yearly_endpoint.py -v

# 3. OpenAPI свежесть
make api-gen

# 4. Live test
make up
time curl "http://localhost:8000/api/v1/predictions/route/7?horizon=year&n_scenarios=100" | jq '.scenarios | length'
# Ожидаем: 12 (месяцев), time < 5 sec
```

## Beneficiary Impact

**Департамент (⭐⭐⭐⭐⭐)** — годовой план = основа для бюджета.
**Планировщик (⭐⭐⭐⭐)** — сценарии "что если" для новых маршрутов.
**Жюри (⭐⭐⭐)** — соответствие ТЗ §3.1.2.

RICE: 1.2 — обязательный для ТЗ.
