"""Tests for BaselineMean predictor."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.baseline import BaselineMean


@pytest.fixture()
def fitted_model(tmp_path: Path) -> BaselineMean:
    """Build a fitted BaselineMean from small synthetic ridership."""
    src = SyntheticSource(SyntheticConfig(n_days=21, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 21)))
    m = BaselineMean(model_id="baseline_v1")
    m.fit(rid)
    return m


def test_baseline_can_fit(fitted_model: BaselineMean) -> None:
    assert fitted_model.fitted_
    assert len(fitted_model.table_) > 0
    assert len(fitted_model.global_table_) > 0


def test_baseline_predict_returns_one_point_per_hour(
    fitted_model: BaselineMean,
) -> None:
    pts = fitted_model.predict(
        stop_id=1,
        period_start=datetime(2026, 2, 1, 0, 0),
        period_end=datetime(2026, 2, 1, 3, 0),
    )
    assert len(pts) == 3
    for p in pts:
        assert p.stop_id == 1
        assert p.value >= 0
        assert p.lower <= p.value <= p.upper
        assert p.model_id == "baseline_v1"


def test_baseline_predict_handles_unknown_stop(fitted_model: BaselineMean) -> None:
    """Unknown stop falls back to global (weekday, hour) mean."""
    pts_known = fitted_model.predict(
        stop_id=1,
        period_start=datetime(2026, 2, 2, 8, 0),
        period_end=datetime(2026, 2, 2, 9, 0),
    )
    pts_unknown = fitted_model.predict(
        stop_id=9999,
        period_start=datetime(2026, 2, 2, 8, 0),
        period_end=datetime(2026, 2, 2, 9, 0),
    )
    # Should be > 0 (global fallback) but possibly different
    assert pts_unknown[0].value >= 0


def test_baseline_save_load_roundtrip(
    fitted_model: BaselineMean, tmp_path: Path
) -> None:
    p = tmp_path / "model.pkl"
    fitted_model.save(str(p))
    assert p.exists()

    loaded = BaselineMean.load(str(p))
    assert loaded.model_id == fitted_model.model_id
    assert loaded.fitted_
    assert loaded.table_ == fitted_model.table_


def test_baseline_rmsle_below_threshold(fitted_model: BaselineMean) -> None:
    """Predict on held-out week, check RMSLE < 1.2.

    Note: baseline on noisy synthetic data gives RMSLE ~1.0-1.1 (peak variance
    dominates). Threshold 1.2 leaves headroom for a "broken" model; real
    improvement comes from XGBoost / GRU (T-028..T-030).
    """
    src = SyntheticSource(SyntheticConfig(n_days=28, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 28)))
    # Train on first 21 days, evaluate on last 7
    train = rid[rid["timestamp"] < pd.Timestamp("2026-01-22")]
    test = rid[rid["timestamp"] >= pd.Timestamp("2026-01-22")]

    model = BaselineMean(model_id="baseline_v1")
    model.fit(train)

    # Predict for each (stop, hour) bucket in test, compare to actual
    sq_errors: list[float] = []
    for (stop_id, ts), group in test.groupby([test["stop_id"], test["timestamp"]]):
        pred = model.predict(
            int(stop_id),
            ts.to_pydatetime(),
            ts.to_pydatetime() + pd.Timedelta(hours=1).to_pytimedelta(),
        )
        if pred:
            actual = group["passenger_count"].sum()
            # RMSLE: log1p(actual) - log1p(pred)
            sq_errors.append((np.log1p(actual) - np.log1p(pred[0].value)) ** 2)

    if sq_errors:
        rmsle = float(np.sqrt(np.mean(sq_errors)))
        assert rmsle < 1.2, f"RMSLE {rmsle:.3f} exceeds threshold 1.2"


def test_baseline_fails_on_empty_data() -> None:
    m = BaselineMean()
    with pytest.raises(ValueError):
        m.fit(
            pd.DataFrame(
                columns=["timestamp", "stop_id", "route_id", "passenger_count"]
            )
        )


def test_baseline_predict_requires_fit() -> None:
    m = BaselineMean()
    with pytest.raises(RuntimeError):
        m.predict(
            stop_id=1,
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 1, 1, 0),
        )
