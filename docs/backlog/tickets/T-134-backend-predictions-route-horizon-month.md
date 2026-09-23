---
id: T-134
phase: 1
title: apps/backend — GET /api/v1/predictions/route/{id}?horizon=month (среднесрочный прогноз)
priority: P1
effort: 4
unit: hours
rice:
  R: 4
  I: 2.0
  C: 0.7
  score: 1.4
depends_on: [T-019, T-031]
blocks: []
tags: [backend, api, predictions, horizon, month, beneficiary, hackathon]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-134: backend — endpoint /api/v1/predictions/route/{id}?horizon=month

## Context

ТЗ §3.1.2 (прямое требование):
> «Среднесрочный (1 месяц) – ежедневный прогноз с учётом сезонности, праздников, погодных
> факторов.»

ТЗ §7.2 (метрика):
> «Для среднесрочного (1 месяц) RMSLE < 0.50.»

Сейчас:
- `apps/backend/app/api/predictions.py::get_predictions_for_stop` возвращает `horizon: "day"` **захардкожено** (строка 80).
- OpenAPI не имеет `horizon` параметра, нет endpoint `/predictions/route/{id}`.
- README.md и AGENTS.md обещают «три горизонта (день/месяц/год)» — обещание без реализации.

Решает user story:
> «Как аналитик Департамента, я хочу видеть прогноз на месяц вперёд по маршруту, чтобы
>  планировать распределение подвижного состава и ремонтные окна.»

## Acceptance Criteria

- [ ] Endpoint `GET /api/v1/predictions/route/{route_id}?horizon=month&from=YYYY-MM-DD&to=YYYY-MM-DD`
- [ ] Параметры:
  - `route_id: int` (path, 1..N)
  - `horizon: Literal["day", "month"]` (query, default "month" если from+to в месячном диапазоне)
  - `from: date` (query, optional, default = today)
  - `to: date` (query, optional, default = from + 30 days)
- [ ] Response: Pydantic `MonthlyPredictionsResponse`:
  - `route_id: int`
  - `horizon: "month"`
  - `granularity: "day"`
  - `model_id: str`
  - `data: list[DailyPoint]` где `DailyPoint`:
    - `date: date` (ISO)
    - `value: float` (прогноз пассажиропотока за день)
    - `lower: float`, `upper: float` (CI)
    - `day_of_week: int`
    - `is_holiday: bool` (опционально)
- [ ] Активная модель из registry через `_get_predictor(loader)` (тот же dispatcher что в T-127)
- [ ] При `kind != "baseline"` и `!= "xgboost"` — 501 (согласовано с T-042, T-127)
- [ ] При отсутствии активного артефакта — 503
- [ ] Валидация: `from < to`, диапазон ≤ 90 дней
- [ ] `make api-gen` обновляет `docs/api/openapi.json` (+1 path)
- [ ] `make fe-gen` создаёт hook `useGetPredictionsRouteApiV1PredictionsRouteRouteIdGet` в `apps/frontend/src/generated/`
- [ ] Unit-тесты: `apps/backend/tests/test_monthly_endpoint.py` (5+ кейсов: happy path, validation, 503, 501)
- [ ] Документация в OpenAPI: примеры, описание, ссылки на T-042 и T-127

## Technical Notes

Переиспользовать из T-127:
```python
# apps/backend/app/schemas/predictions.py
class DailyPoint(BaseModel):
    date: date
    value: float
    lower: float
    upper: float
    day_of_week: int
    is_holiday: bool = False

class MonthlyPredictionsResponse(BaseModel):
    route_id: int
    horizon: Literal["month"]
    granularity: Literal["day"]
    model_id: str
    data: list[DailyPoint]
```

Реализация (по аналогии с T-127, app/api/predictions.py):
```python
@router.get(
    "/predictions/route/{route_id}",
    response_model=MonthlyPredictionsResponse,
    summary="Monthly ridership predictions for a route",
)
def get_monthly_predictions(
    route_id: int = Path(..., ge=1),
    from_: date | None = Query(None, alias="from", description="Start date (inclusive)"),
    to: date | None = Query(None, description="End date (inclusive)"),
    horizon: Literal["month"] = Query("month"),
    loader: ArtifactLoader = Depends(get_loader),
) -> MonthlyPredictionsResponse:
    ...
```

Использует существующий XGBoostPredictor.predict() — он возвращает hourly точки,
агрегируем в daily (sum по дню). Реализация аналогична `get_eta_predictions` в T-127.

**Важно:** `from` — Python keyword, поэтому используем alias `from_` и `Query(alias="from")`.

## Verification

```bash
# 1. Type-check
uv run mypy apps/backend/app/

# 2. Unit + integration tests
uv run pytest apps/backend/tests/test_monthly_endpoint.py -v
# Ожидаем: 5+ тестов зелёные

# 3. OpenAPI свежесть
make api-gen
git diff docs/api/openapi.json
# Ожидаем: +1 path /api/v1/predictions/route/{route_id}

# 4. Live test (после make up)
make up
curl "http://localhost:8000/api/v1/predictions/route/7?from=2026-10-01&to=2026-10-31" | jq
# Ожидаем: JSON с 31 точкой (data[].date от 01 до 31 октября)

# 5. Frontend hook доступен
make fe-gen
grep -l "useGetPredictionsRoute" apps/frontend/src/generated/api.ts
# Ожидаем: файл найден
```

## Beneficiary Impact

**Департамент (⭐⭐⭐⭐)** — месячный прогноз = планирование ремонтов и распределения составов.
**Аналитики (⭐⭐⭐)** — сезонные тренды, подготовка отчётов.
**Жюри (⭐⭐⭐)** — соответствие ТЗ §3.1.2 (3 горизонта).

RICE: 1.4 — средний, но **обязательный для ТЗ**. Делается в Фазе 1.
