---
id: T-144
phase: 2
title: WAPE-score в ml/transit_ai/reports/metrics.py (primary metric хакатона)
priority: P0
effort: 1
unit: hours
rice:
  R: 10
  I: 3.0
  C: 1.0
  score: 10.00
depends_on: [T-143]
blocks: [T-145]
tags: [ml, metrics, wape, hackathon, primary-metric, p0]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-144: WAPE-score в metrics.py (D-016, F-016)

## Context

Организаторы подтвердили: primary метрика хакатона = **WAPE-score** ∈ [0,1],
больше — лучше, baseline ≈ 0.48. Формула: `WAPE = Σ|y−ŷ| / Σy`,
`WAPE-score = max(0, 1 − WAPE)`.

D-016: WAPE-score становится primary в `compute_metrics()`, RMSLE/MAE/MAPE —
diagnostics. Это даст соответствие отчёта жюри метрике платформы.

Существующая `ml/transit_ai/reports/metrics.py` уже содержит `rmsle/mae/mape` —
расширяем, не переписываем.

## Acceptance Criteria

- [ ] `ml/transit_ai/reports/metrics.py` добавляет функции:
  - `wape(y_true, y_pred) -> float`  — Σ|y−ŷ| / Σy
  - `wape_score(y_true, y_pred) -> float` — max(0, 1 − WAPE)
- [ ] `compute_metrics()` возвращает `{rmsle, mae, mape, wape, wape_score}`
- [ ] WAPE устойчив к y=0 (Σy в знаменателе игнорирует строки с y=0? НЕТ: формула
  платформы суммирует ВСЕ строки; если Σy=0, делим на 0 → вернуть wape=inf, score=0)
- [ ] Unit-тест `ml/tests/test_metrics_wape.py`: 5+ кейсов:
  - perfect prediction (WAPE=0, score=1)
  - 50% error (WAPE=0.5, score=0.5)
  - all zeros y_true (WAPE=inf или score=0, не падать)
  - negative predictions (clipped to 0)
  - empty arrays (WAPE=0, score=1)
- [ ] Все 4 существующих теста metrics продолжают проходить

## Technical Notes

```python
# ml/transit_ai/reports/metrics.py
def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error: Σ|y−ŷ| / Σy.

    Устойчив к разбросу объёмов между маршрутами и нулевым ночным часам.
    Возвращает inf если Σy == 0 (см. wape_score для max(0, 1-WAPE)).
    """
    if len(y_true) == 0 or len(y_pred) == 0:
        return 0.0
    y_true = np.maximum(y_true, 0)
    y_pred = np.maximum(y_pred, 0)
    denom = float(y_true.sum())
    if denom == 0.0:
        return float("inf")
    return float(np.abs(y_true - y_pred).sum() / denom)


def wape_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Hackathon primary metric: max(0, 1 − WAPE) ∈ [0, 1].

    Baseline ≈ 0.48 (пол). Цель: > 0.70 (8/10 баллов).
    """
    w = wape(y_true, y_pred)
    if w == float("inf"):
        return 0.0
    return float(max(0.0, 1.0 - w))


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Единая точка входа: {rmsle, mae, mape, wape, wape_score}.

    Пустые массивы → нули (no crash).
    """
    if len(y_true) == 0 or len(y_pred) == 0:
        return {"rmsle": 0.0, "mae": 0.0, "mape": 0.0, "wape": 0.0, "wape_score": 0.0}
    return {
        "rmsle": rmsle(y_true, y_pred),
        "mae": mae(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "wape": wape(y_true, y_pred),
        "wape_score": wape_score(y_true, y_pred),
    }
```

## Verification

```bash
uv run pytest ml/tests/test_metrics_wape.py -v
# 5+ тестов зелёные

uv run pytest ml/tests/test_metrics.py -v
# Существующие тесты продолжают работать
```

## Beneficiary Impact

**Жюри (⭐⭐⭐)** — primary метрика = то, что считает платформа.
**Команда (⭐⭐⭐)** — единая метрика для всех экспериментов.

RICE: 10.00 — максимальный приоритет, делается ПЕРВЫМ после T-143.
