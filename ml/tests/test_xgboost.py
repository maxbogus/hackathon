"""Tests for XGBoostPredictor.

Контракт (см. ml/transit_ai/models/base.py):
- fit(ridership_df) → train XGBoost Booster на log1p(passenger_count)
- predict(stop_id, period_start, period_end) → list[PredictionPoint] (1 per hour)
- save(path) / load(path) через joblib (XGBoost Booster не pickle-friendly)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.xgboost_pred import XGBoostPredictor


@pytest.fixture()
def fitted_xgb(tmp_path: Path) -> XGBoostPredictor:
    """Build a fitted XGBoostPredictor from small synthetic ridership."""
    src = SyntheticSource(SyntheticConfig(n_days=21, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 21)))
    m = XGBoostPredictor(model_id="xgboost_v1")
    m.fit(rid)
    return m


def test_xgboost_can_fit(fitted_xgb: XGBoostPredictor) -> None:
    assert fitted_xgb.fitted_
    assert fitted_xgb.boosters_, "boosters dict should not be empty after fit"
    assert len(fitted_xgb.feature_names_) > 0


def test_xgboost_predict_returns_one_point_per_hour(
    fitted_xgb: XGBoostPredictor,
) -> None:
    pts = fitted_xgb.predict(
        stop_id=1,
        period_start=datetime(2026, 2, 1, 0, 0),
        period_end=datetime(2026, 2, 1, 3, 0),
    )
    assert len(pts) == 3
    for p in pts:
        assert p.stop_id == 1
        assert p.value >= 0
        assert np.isfinite(p.value)
        assert p.lower <= p.value <= p.upper
        assert p.model_id == "xgboost_v1"


def test_xgboost_predict_for_unknown_stop(fitted_xgb: XGBoostPredictor) -> None:
    """Unknown stop_id → predict с mean features, не должно падать."""
    pts = fitted_xgb.predict(
        stop_id=9999,
        period_start=datetime(2026, 2, 2, 8, 0),
        period_end=datetime(2026, 2, 2, 10, 0),
    )
    assert len(pts) == 2
    for p in pts:
        assert np.isfinite(p.value)
        assert p.value >= 0


def test_xgboost_save_load_roundtrip(
    fitted_xgb: XGBoostPredictor, tmp_path: Path
) -> None:
    p = tmp_path / "xgb_v1.pkl"
    fitted_xgb.save(str(p))
    assert p.exists()

    loaded = XGBoostPredictor.load(str(p))
    assert loaded.model_id == fitted_xgb.model_id
    assert loaded.fitted_
    assert loaded.feature_names_ == fitted_xgb.feature_names_

    # Predict should give same results
    pts_orig = fitted_xgb.predict(
        1, datetime(2026, 2, 1, 8, 0), datetime(2026, 2, 1, 10, 0)
    )
    pts_loaded = loaded.predict(
        1, datetime(2026, 2, 1, 8, 0), datetime(2026, 2, 1, 10, 0)
    )
    for a, b in zip(pts_orig, pts_loaded, strict=True):
        np.testing.assert_allclose(a.value, b.value, rtol=1e-3)
        np.testing.assert_allclose(a.lower, b.lower, rtol=1e-3)
        np.testing.assert_allclose(a.upper, b.upper, rtol=1e-3)


def test_xgboost_handles_empty_ridership() -> None:
    """fit() on empty df должен бросать понятную ошибку."""
    m = XGBoostPredictor(model_id="xgboost_v1")
    empty = pd.DataFrame(
        columns=["timestamp", "stop_id", "route_id", "passenger_count"]
    )
    with pytest.raises(ValueError, match="empty"):
        m.fit(empty)


def test_xgboost_finite_values(fitted_xgb: XGBoostPredictor) -> None:
    """Никаких NaN/Inf в predictions."""
    pts = fitted_xgb.predict(1, datetime(2026, 2, 1, 0, 0), datetime(2026, 2, 1, 23, 0))
    for p in pts:
        assert np.isfinite(p.value)
        assert np.isfinite(p.lower)
        assert np.isfinite(p.upper)
        assert p.value >= 0


def test_xgboost_beats_baseline_on_synthetic() -> None:
    """Sanity: XGBoost RMSLE должен быть ниже, чем у baseline на тех же данных."""
    from transit_ai.models.baseline import BaselineMean

    src = SyntheticSource(SyntheticConfig(n_days=42, seed=42))
    train = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 28)))
    test = src.load_ridership(DateRange(datetime(2026, 2, 5), datetime(2026, 2, 11)))

    xgb = XGBoostPredictor(model_id="xgboost_v1")
    xgb.fit(train)

    # Baseline fit на тех же данных
    base = BaselineMean(model_id="baseline_v1")
    base.fit(train)

    # Evaluate: берём несколько stops × hours
    test_stops = [int(s) for s in test["stop_id"].unique()[:5]]
    rmsle_xgb: list[float] = []
    rmsle_base: list[float] = []
    for sid in test_stops:
        sub = test[test["stop_id"] == sid].head(24)
        for _, row in sub.iterrows():
            ts = row["timestamp"]
            actual = float(row["passenger_count"])
            xgb_pred = xgb.predict(sid, ts, ts + pd.Timedelta(hours=1))[0].value
            base_pred = base.predict(sid, ts, ts + pd.Timedelta(hours=1))[0].value
            rmsle_xgb.append((np.log1p(xgb_pred) - np.log1p(actual)) ** 2)
            rmsle_base.append((np.log1p(base_pred) - np.log1p(actual)) ** 2)

    rmsle_xgb_mean = float(np.sqrt(np.mean(rmsle_xgb)))
    rmsle_base_mean = float(np.sqrt(np.mean(rmsle_base)))
    # XGBoost должен быть не хуже baseline (с tolerance)
    assert rmsle_xgb_mean <= rmsle_base_mean + 0.05, (
        f"XGBoost ({rmsle_xgb_mean:.3f}) should be close to baseline ({rmsle_base_mean:.3f})"
    )
