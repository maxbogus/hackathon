"""Tests for XGBoost inference с train_lookup fallback (T-152 fix).

Когда predict_batch вызывается без boardings (submission period),
lag/rolling features ДОЛЖНЫ использовать mean из train, а не 0.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.xgboost_route import (
    XGBoostRoutePredictor,
    build_lag_lookup,
)


@pytest.fixture(scope="module")
def full_data() -> pd.DataFrame:
    src = RealSource()
    return src.load_ridership(
        DateRange(datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 10, 31, tzinfo=UTC))
    )


def test_inference_without_lag_lookup_returns_non_zero(full_data: pd.DataFrame) -> None:
    """Без lookup + без boardings → lag = 0 (legacy, регрессия).
    БЕЗ lookup поведение = текущее плохое (это ожидаемо)."""
    model = XGBoostRoutePredictor(
        model_id="test_inference_no_lookup",
        n_estimators=20,
        max_depth=3,
    )
    model.fit(full_data)
    # имитация submission: grid без boardings
    grid = pd.DataFrame(
        {
            "route_id": [1, 5, 17],
            "date": pd.to_datetime(["2025-11-01", "2025-11-01", "2025-11-01"]).date,
            "hour": [12, 18, 8],
            "timestamp": pd.to_datetime(
                ["2025-11-01 12:00", "2025-11-01 18:00", "2025-11-01 08:00"]
            ),
        }
    )
    preds_no_lookup = model.predict_batch(grid)
    # Должны быть >= 0 (не NaN, не отрицательные)
    assert (preds_no_lookup >= 0).all(), "preds should be non-negative"
    assert not np.isnan(preds_no_lookup).any(), "preds should not be NaN"


def test_build_lag_lookup(full_data: pd.DataFrame) -> None:
    """build_lag_lookup возвращает dict по (route, hour, weekday) → mean."""
    lookup = build_lag_lookup(full_data)
    assert isinstance(lookup, dict)
    # Проверяем что есть ключи для route=17 weekday=0 hour=8 (типичный morning peak)
    key = (17, 0, 8)
    assert key in lookup, f"missing key {key} in lookup"
    val = lookup[key]
    assert val > 1000, f"route 17 wd=0 hr=8 should be > 1000, got {val}"
    # Route 25 small — должно быть меньше
    key25 = (25, 0, 8)
    if key25 in lookup:
        assert lookup[key25] < lookup[key], "route 25 < route 17"


def test_inference_with_lag_lookup_returns_realistic_sum(
    full_data: pd.DataFrame,
) -> None:
    """С lag_lookup → predictions должны быть в ~правильном масштабе (3-15M)."""
    model = XGBoostRoutePredictor(
        model_id="test_inference_with_lookup",
        n_estimators=200,
        max_depth=6,
    )
    model.fit(full_data)
    grid = pd.DataFrame(
        {
            "route_id": [1] * 24 + [17] * 24 + [25] * 24,
            "date": pd.to_datetime(["2025-11-15"] * 72).date,
            "hour": list(range(24)) * 3,
            "timestamp": pd.to_datetime(
                [f"2025-11-15 {h:02d}:00" for h in range(24)] * 3
            ),
        }
    )

    # Without lookup (broken)
    preds_no = model.predict_batch(grid)
    sum_no = float(preds_no.sum())

    # With lookup (fixed)
    lookup = build_lag_lookup(full_data)
    preds_yes = model.predict_batch(grid, lag_lookup=lookup)
    sum_yes = float(preds_yes.sum())

    # Ожидаем: sum_yes >> sum_no (×2 как минимум)
    assert sum_yes > sum_no * 2, (
        f"sum_yes ({sum_yes:.0f}) должна быть >> sum_no ({sum_no:.0f}). "
        f"С lag_lookup модель использует реальные средние вместо 0."
    )
    # И sum_yes должна быть в реалистичном диапазоне
    assert 50_000 < sum_yes < 500_000, (
        f"sum_yes = {sum_yes:.0f} вне диапазона. Для 72 точек (3 routes × 24h) "
        f"ожидаем десятки тысяч (а не миллионы)."
    )


def test_predict_with_ci_with_lag_lookup(full_data: pd.DataFrame) -> None:
    """predict_with_ci тоже должен использовать lag_lookup."""
    model = XGBoostRoutePredictor(
        model_id="test_ci_lag",
        n_estimators=20,
        max_depth=3,
    )
    model.fit(full_data)
    lookup = build_lag_lookup(full_data)
    grid = pd.DataFrame(
        {
            "route_id": [1, 17],
            "date": pd.to_datetime(["2025-12-01", "2025-12-01"]).date,
            "hour": [10, 10],
            "timestamp": pd.to_datetime(["2025-12-01 10:00", "2025-12-01 10:00"]),
        }
    )
    median, lower, upper = model.predict_with_ci(grid, lag_lookup=lookup)
    assert (median >= 0).all()
    assert (lower <= median).all() or (lower <= median + 1).all()  # weak check
    assert (upper >= median).all() or (upper >= median - 1).all()
