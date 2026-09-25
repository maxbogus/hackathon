---
id: T-146
phase: 2
title: per-route WAPE диагностика — найти слабые маршруты перед улучшением
priority: P0
effort: 1
unit: hours
rice:
  R: 8
  I: 3.0
  C: 1.0
  score: 8.00
depends_on: [T-145]
blocks: [T-147]
tags: [ml, diagnostics, per-route, hackathon, p0]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-146: per-route WAPE диагностика (F-019)

## Context

После F-019 (submission #1 → WAPE=0.72568 на платформе) нужно понять, какие
маршруты дают наибольшую ошибку. Это выявит, нужен ли per-route calibration
(T-147) и/или больше фичей для конкретных маршрутов.

Гипотезы:
- **route=5**: cold-start fallback на global mean → высокая ошибка.
- **route=17** (самый загруженный, 2.1k boardings/hour): возможно модель
  занижает пик (mean не ловит пики).
- **route=25** (самый лёгкий, 337 boardings/hour): возможны шумовые выбросы.

## Acceptance Criteria

- [ ] `ml/transit_ai/reports/diagnose.py` с функцией:
  - `per_route_wape(test_df, predictions) -> dict[int, float]`
  - `per_hour_wape(test_df, predictions) -> dict[int, float]`
  - `per_weekday_wape(test_df, predictions) -> dict[int, float]`
  - `diagnose(test_df, predictions) -> dict` (всё вместе)
- [ ] `ml/scripts/diagnose_per_route.py` CLI:
  - `uv run --directory ml python scripts/diagnose_per_route.py`
  - Печатает: overall WAPE, per-route, per-hour, per-weekday
  - Указывает слабые места (WAPE < 0.85)
- [ ] `make diagnose` target
- [ ] Unit-тест `ml/tests/test_diagnose.py`: 5+ кейсов:
  - Идеальный прогноз → все WAPE=1.0
  - 50% ошибка только на route=1 → per_route[1] = 0.5
  - 50% ошибка только на hour=8 → per_hour[8] = 0.5
  - Пустой DF → returns {}
  - Сумма per-route * Σy[route] должна быть = overall WAPE * Σy

## Technical Notes

```python
"""Per-route/per-hour/per-weekday WAPE диагностика (T-146)."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd


def per_route_wape(
    test_df: pd.DataFrame, predictions: np.ndarray
) -> dict[int, float]:
    """Per-route WAPE-score = max(0, 1 - Σ|y-ŷ|/Σy) для каждого route_id."""
    if len(test_df) == 0:
        return {}
    df = test_df.copy()
    df["__pred__"] = predictions
    out: dict[int, float] = {}
    for route, group in df.groupby("route_id"):
        y = group["boardings"].values
        yhat = group["__pred__"].values
        denom = float(y.sum())
        if denom == 0:
            out[int(route)] = 0.0
            continue
        wape = float(np.abs(y - yhat).sum() / denom)
        out[int(route)] = float(max(0.0, 1.0 - wape))
    return out


def per_hour_wape(
    test_df: pd.DataFrame, predictions: np.ndarray
) -> dict[int, float]:
    df = test_df.copy()
    df["__pred__"] = predictions
    out: dict[int, float] = {}
    for hour, group in df.groupby("hour"):
        y = group["boardings"].values
        yhat = group["__pred__"].values
        denom = float(y.sum())
        if denom == 0:
            out[int(hour)] = 0.0
            continue
        wape = float(np.abs(y - yhat).sum() / denom)
        out[int(hour)] = float(max(0.0, 1.0 - wape))
    return out


def per_weekday_wape(
    test_df: pd.DataFrame, predictions: np.ndarray
) -> dict[int, float]:
    df = test_df.copy()
    df["__pred__"] = predictions
    if "weekday" not in df.columns:
        df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
    out: dict[int, float] = {}
    for wd, group in df.groupby("weekday"):
        y = group["boardings"].values
        yhat = group["__pred__"].values
        denom = float(y.sum())
        if denom == 0:
            out[int(wd)] = 0.0
            continue
        wape = float(np.abs(y - yhat).sum() / denom)
        out[int(wd)] = float(max(0.0, 1.0 - wape))
    return out


def diagnose(test_df: pd.DataFrame, predictions: np.ndarray) -> dict:
    """Полная диагностика: overall + per-route + per-hour + per-weekday."""
    if len(test_df) == 0:
        return {
            "overall": 0.0,
            "per_route": {},
            "per_hour": {},
            "per_weekday": {},
            "n_points": 0,
        }
    y = test_df["boardings"].values
    denom = float(y.sum())
    overall_wape = float(np.abs(y - predictions).sum() / denom) if denom > 0 else 0.0
    return {
        "overall": float(max(0.0, 1.0 - overall_wape)),
        "per_route": per_route_wape(test_df, predictions),
        "per_hour": per_hour_wape(test_df, predictions),
        "per_weekday": per_weekday_wape(test_df, predictions),
        "n_points": len(test_df),
        "total_boardings": denom,
    }


__all__ = [
    "per_route_wape",
    "per_hour_wape",
    "per_weekday_wape",
    "diagnose",
]
```

## Verification

```bash
make diagnose
# → показывает overall + per-route (отсортировано по WAPE ASC) + per-hour + per-weekday

uv run pytest ml/tests/test_diagnose.py -v
# 5+ тестов зелёные
```

## Beneficiary Impact

**Команда (⭐⭐⭐)** — точечные улучшения вместо «общих».
**WAPE-score** — фокус на слабых маршрутах.

RICE: 8.00 — высокий приоритет, делается ПЕРВЫМ после F-019.
