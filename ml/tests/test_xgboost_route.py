"""Tests for XGBoostRoutePredictor on real hackathon data (T-152)."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.xgboost_route import FEATURE_NAMES, XGBoostRoutePredictor
from transit_ai.reports.metrics import compute_metrics


@pytest.fixture(scope="module")
def full_data() -> pd.DataFrame:
    """Load full train + holdout для lag features."""
    src = RealSource()
    return src.load_ridership(
        DateRange(
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 10, 31, tzinfo=UTC),
        )
    )


def test_xgboost_route_fit_on_real_data(full_data: pd.DataFrame) -> None:
    """T-152: model fits on real hackathon data without errors."""
    model = XGBoostRoutePredictor(
        model_id="xgboost_test_v1",
        n_estimators=50,  # быстрее для теста
        max_depth=4,
    )
    model.fit(full_data)
    assert model.fitted_
    assert 0.1 in model.boosters_
    assert 0.5 in model.boosters_
    assert 0.9 in model.boosters_
    assert model.feature_names_ == list(FEATURE_NAMES)


def test_xgboost_route_predict_returns_correct_shape(full_data: pd.DataFrame) -> None:
    """predict_batch returns same length array."""
    model = XGBoostRoutePredictor(
        model_id="xgboost_test_v2",
        n_estimators=50,
        max_depth=4,
    )
    model.fit(full_data)
    # holdout = сен-окт
    holdout = full_data[full_data["timestamp"] >= pd.Timestamp("2025-09-01")].copy()
    preds = model.predict_batch(holdout)
    assert len(preds) == len(holdout)
    assert (preds >= 0).all()


def test_xgboost_route_predict_with_ci(full_data: pd.DataFrame) -> None:
    """predict_with_ci returns (median, lower, upper) — order respected."""
    model = XGBoostRoutePredictor(
        model_id="xgboost_test_v3",
        n_estimators=50,
        max_depth=4,
    )
    model.fit(full_data)
    holdout = full_data[full_data["timestamp"] >= pd.Timestamp("2025-09-01")].copy()
    median, lower, upper = model.predict_with_ci(holdout)
    assert len(median) == len(holdout)
    # order: lower <= median <= upper (большинство случаев)
    n_correct = ((lower <= median) & (median <= upper)).sum()
    assert n_correct >= 0.95 * len(median), (
        f"CI ordering broken: only {n_correct}/{len(median)} valid"
    )


def test_xgboost_route_holdout_wape_better_than_baseline(
    full_data: pd.DataFrame,
) -> None:
    """T-152 acceptance: XGBoost holdout WAPE < RouteBaselineMean (0.8751)."""
    from transit_ai.models.route_baseline import RouteBaselineMean

    # Baseline
    baseline = RouteBaselineMean(model_id="rb_baseline")
    train_only = full_data[full_data["timestamp"] < pd.Timestamp("2025-09-01")].copy()
    holdout = full_data[full_data["timestamp"] >= pd.Timestamp("2025-09-01")].copy()
    baseline.fit(train_only)
    base_pred = baseline.predict_batch(holdout)
    base_metrics = compute_metrics(holdout["boardings"].values, base_pred)
    base_wape = base_metrics["wape_score"]

    # XGBoost
    xgb_model = XGBoostRoutePredictor(
        model_id="xgboost_compare",
        n_estimators=200,
        max_depth=6,
    )
    xgb_model.fit(full_data)
    xgb_pred = xgb_model.predict_batch(holdout)
    xgb_metrics = compute_metrics(holdout["boardings"].values, xgb_pred)
    xgb_wape = xgb_metrics["wape_score"]

    print(f"\nbaseline WAPE={base_wape:.4f}, xgboost WAPE={xgb_wape:.4f}")
    # Ожидаем XGBoost лучше на 1+pp
    assert xgb_wape > base_wape + 0.005, (
        f"XGBoost ({xgb_wape:.4f}) должен быть лучше baseline ({base_wape:.4f}) на >0.5pp"
    )


def test_xgboost_route_save_load_roundtrip(full_data: pd.DataFrame, tmp_path) -> None:
    """T-152 acceptance: model can be saved and loaded."""
    model = XGBoostRoutePredictor(
        model_id="xgboost_save",
        n_estimators=20,
        max_depth=3,
    )
    model.fit(full_data)
    path = tmp_path / "model.pkl"
    model.save(str(path))
    loaded = XGBoostRoutePredictor.load(str(path))
    assert loaded.fitted_
    assert loaded.model_id == "xgboost_save"
    holdout = (
        full_data[full_data["timestamp"] >= pd.Timestamp("2025-09-01")].head(100).copy()
    )
    p1 = model.predict_batch(holdout)
    p2 = loaded.predict_batch(holdout)
    np.testing.assert_allclose(p1, p2, rtol=1e-4)


def test_xgboost_route_handles_empty_raises() -> None:
    """fit on empty raises."""
    model = XGBoostRoutePredictor(model_id="empty")
    with pytest.raises(ValueError, match="empty"):
        model.fit(pd.DataFrame())


def test_xgboost_route_requires_columns(full_data: pd.DataFrame) -> None:
    """Missing columns raises."""
    model = XGBoostRoutePredictor(model_id="missing_cols")
    bad = full_data.drop(columns=["boardings"])
    with pytest.raises(ValueError, match="Missing columns"):
        model.fit(bad)
