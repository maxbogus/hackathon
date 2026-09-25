---
id: T-147
phase: 2
title: per-route calibration — bias correction на основе F-020 (per-route WAPE диагностика)
priority: P0
effort: 2
unit: hours
rice:
  R: 10
  I: 3.0
  C: 0.9
  score: 13.50
depends_on: [T-146]
blocks: []
tags: [ml, calibration, per-route, hackathon, p0, wape]
status: in-progress
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-147: per-route calibration — bias correction (F-020)

## Context

**F-020 (T-146 диагностика):** per-route WAPE на holdout показал, что 4 маршрута
слабее остальных (WAPE-score < 0.85):
- **route 25**: 0.7977 (слабейший, 337 boardings/hour — лёгкий)
- **route 50**: 0.8087 (edge route)
- **route 7**:  0.8306
- **route 28**: 0.8353

Submission #1 → WAPE=0.72568 на платформе. Per-route calibration должна поднять
его до **0.78-0.80** за счёт исправления систематического bias по маршрутам.

Также этот тикет покрывает **Критерий 2в** ТЗ хакатона: «в интерфейсе есть
возможность менять корректирующие коэффициенты (поправка на погоду/событие/сезон)
и сразу видеть, как меняется прогноз (+1)» — **+2 балла**.

## Acceptance Criteria

### Часть A: Bias correction (backend) — DONE ✅

- [x] `ml/transit_ai/calibration/route_bias.py` с функцией:
  - `compute_route_bias(train_actual, train_pred) -> dict[int, float]`
  - `apply_route_bias(predictions, route_ids, biases) -> np.ndarray`
  - bias = median(log1p(actual) - log1p(pred)) per route (log-space стабильнее)
- [x] Edge case: новый маршрут (нет в train) → bias = 0 (нейтральная коррекция, multiplier=1.0)
- [x] Edge case: train пустой → raise ValueError с понятным сообщением
- [x] Edge case: predictions мутирует? — нет, делает `.copy()` defensive
- [x] Edge case: очень отрицательный bias → exp(bias)≈0 → clip to 0 (нет отрицательных)
- [x] Unit-тест `ml/tests/test_route_bias.py` — **7/7 passed**:
  - perfect predictions → bias=0 для всех routes
  - занижение в 2 раза → positive log bias (~0.685)
  - unknown route в apply → bias=0, коррекция=1.0
  - bias=-100 → clip to 0 (нет отрицательных)
  - empty DataFrame → ValueError
  - input array не мутируется
  - end-to-end: bias улучшает WAPE с 0.5 до <0.1

### Часть B: К2.в — корректирующие коэффициенты в API + UI — DEFERRED ⏳

- [ ] Backend: `apps/backend/app/api/predictions.py` — GET `/api/v1/predictions/route/{id}` с query params
- [ ] Frontend: dispatcher mode — слайдеры coef_weather / coef_event / coef_season
- [ ] Unit-тест для API

> **Причина отсрочки:** hard deadline submission 27.09. Bias correction даёт +0.7pp
> на holdout (in-sample оптимистично). Frontend-слайдеры — polish, который
> не влияет на platform score (К1), но нужен для К2.в. **TODO: сделать в следующей сессии.**

### Часть C: Re-submit + ledger — DONE ✅ (backend часть)

- [x] `make submission` обновлён: bias-correction применяется ПЕРЕД записью CSV
- [x] `make diagnose` обновлён: показывает biases + Δ WAPE calibrated vs base
- [x] Submission.csv сгенерирован для submission #2
- [ ] Submission.csv залит на платформу (нужно вручную), WAPE-score зафиксирован в F-021
- [x] D-023 в ledger: per-route bias correction в log-space
- [x] docs/reports/diagnose_per_route.md обновлён

## Technical Notes

### Bias computation (log-space, стабильно)

```python
import numpy as np
import pandas as pd

def compute_route_bias(
    train_actual: pd.Series,
    train_pred: pd.Series,
    route_ids: pd.Series,
) -> dict[int, float]:
    """bias = median(log1p(actual) - log1p(pred)) per route.
    
    Returns:
        {route_id: bias} — bias=0 → нейтральная коррекция (exp(0)=1).
    """
    if len(train_actual) == 0:
        raise ValueError("Cannot compute bias on empty training data")
    df = pd.DataFrame({
        "actual": train_actual.values,
        "pred": train_pred.values,
        "route_id": route_ids.values,
    })
    df["log_actual"] = np.log1p(df["actual"].clip(lower=0))
    df["log_pred"] = np.log1p(df["pred"].clip(lower=0))
    df["log_bias"] = df["log_actual"] - df["log_pred"]
    return df.groupby("route_id")["log_bias"].median().to_dict()


def apply_route_bias(
    predictions: np.ndarray,
    route_ids: np.ndarray,
    biases: dict[int, float],
) -> np.ndarray:
    """Применяем bias мультипликативно: pred *= exp(bias).
    
    Edge case: route_id не в biases → bias = 0, коррекция = 1.
    """
    out = np.asarray(predictions, dtype=np.float64).copy()
    for i, r in enumerate(route_ids):
        bias = biases.get(int(r), 0.0)
        out[i] *= np.exp(bias)
    return np.maximum(out, 0.0)  # не уходим в отрицательные
```

### Frontend coef slider

```typescript
// apps/frontend/src/components/Dispatcher/CoefSliders.tsx
export function CoefSliders({ onChange }: { onChange: (coefs: Coefs) => void }) {
  const [weather, setWeather] = useState(1.0);
  const [event, setEvent] = useState(1.0);
  const [season, setSeason] = useState(1.0);
  // debounce + push to backend
}
```

### Submission pipeline integration

```python
# ml/scripts/make_submission.py — добавить bias correction
biases = compute_route_bias(train["boardings"], train_pred, train["route_id"])
preds_calibrated = apply_route_bias(preds_for_submission, routes_for_submission, biases)
```

## Verification

```bash
uv run pytest ml/tests/test_route_bias.py -v
# 5+ тестов зелёные

# Re-evaluate with calibration
make diagnose
# → per_route WAPE должен улучшиться на 3-5pp для routes [25, 50, 7, 28]

make submission
# → predictions/submission_route_baseline_calibrated_<date>.csv
# → WAPE на holdout (сен-окт) должен быть > 0.87

# Upload to platform (36 attempts total / 24 successful per day)
# After: F-021 — WAPE=???
```

## Beneficiary Impact

**Команда (⭐⭐⭐⭐⭐)** — рост WAPE-score с 0.72568 → 0.78-0.80 = **+4..+6 баллов по К1 (×2 вес)**.
**Жюри (⭐⭐⭐)** — bias correction = reproducible артефакт (с git_commit).
**Департамент (⭐⭐⭐)** — корректирующие коэффициенты = «ручка» для диспетчера.

RICE: 13.5 — **МАКСИМАЛЬНЫЙ приоритет** (топ-1 в backlog после F-019).
