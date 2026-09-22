"""Tests for ml.transit_ai.training.predict (T-033).

Контракт predict():
- load fitted predictor via ModelRegistry.load
- iterate stop_ids → predictor.predict(stop_id, from_dt, to_dt) → list[PredictionPoint]
- write predictions/<date>_<model_id>.parquet with schema from
  docs/schemas/predictions.schema.json
- CLI default: horizon=day, granularity=hour, from=now, to=now+24h, model_id=active.json
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import jsonschema
import pandas as pd
import pyarrow.parquet as pq
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.schemas import load_predictions_schema
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.baseline import BaselineMean
from transit_ai.training.predict import (
    DEFAULT_GRANULARITY,
    DEFAULT_HORIZON,
    PredictConfig,
    predict,
)
from transit_ai.training.registry import ModelRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def schema() -> dict[str, object]:
    return load_predictions_schema()


@pytest.fixture()
def fitted_artifact(tmp_path: Path) -> Path:
    """Fit a BaselineMean on synthetic and save to tmp_path."""
    src = SyntheticSource(SyntheticConfig(n_days=21, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 21)))
    m = BaselineMean(model_id="baseline_v1")
    m.fit(rid)
    reg = ModelRegistry(tmp_path)
    reg.save(m, seed=42)
    reg.activate("baseline_v1")
    return tmp_path


# ---------- Config ----------


def test_predict_config_defaults() -> None:
    cfg = PredictConfig()
    assert cfg.horizon == DEFAULT_HORIZON == "day"
    assert cfg.granularity == DEFAULT_GRANULARITY == "hour"
    assert cfg.model_id is None


def test_predict_config_is_frozen() -> None:
    cfg = PredictConfig()
    with pytest.raises((AttributeError, Exception)):
        cfg.horizon = "month"  # type: ignore[misc]


# ---------- Schema & shape ----------


def test_predict_writes_parquet_with_correct_schema(
    fitted_artifact: Path, schema: dict[str, object], tmp_path: Path
) -> None:
    from_dt = datetime(2026, 2, 1, 0, 0, 0)
    to_dt = from_dt + timedelta(hours=24)

    cfg = PredictConfig(
        artifacts_dir=fitted_artifact,
        output_dir=tmp_path / "predictions",
        model_id="baseline_v1",
        from_dt=from_dt,
        to_dt=to_dt,
        horizon="day",
        granularity="hour",
        stop_ids=[1, 2, 3],
    )

    out_path = predict(cfg)
    assert out_path.exists()
    assert out_path.suffix == ".parquet"

    df = pq.read_table(out_path).to_pandas()
    expected_cols = {
        "period_start",
        "period_end",
        "stop_id",
        "route_id",
        "value",
        "lower",
        "upper",
        "horizon",
        "granularity",
        "model_id",
    }
    assert set(df.columns) >= expected_cols - {"scenario_id"}

    records = df.copy()
    for col in ("period_start", "period_end"):
        records[col] = pd.to_datetime(records[col]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    # route_id is nullable; convert NaN → None (jsonschema wants null for null type)
    records["route_id"] = (
        records["route_id"].astype(object).where(records["route_id"].notna(), None)
    )
    if "scenario_id" in records.columns:
        records["scenario_id"] = (
            records["scenario_id"]
            .astype(object)
            .where(records["scenario_id"].notna(), None)
        )
    jsonschema.validate(records.to_dict(orient="records"), schema)


def test_predict_emits_one_row_per_stop_per_period(
    fitted_artifact: Path, tmp_path: Path
) -> None:
    from_dt = datetime(2026, 2, 1, 0, 0, 0)
    to_dt = from_dt + timedelta(hours=24)
    cfg = PredictConfig(
        artifacts_dir=fitted_artifact,
        output_dir=tmp_path / "predictions",
        model_id="baseline_v1",
        from_dt=from_dt,
        to_dt=to_dt,
        horizon="day",
        granularity="hour",
        stop_ids=[1, 2, 3],
    )
    df = pq.read_table(predict(cfg)).to_pandas()
    assert len(df) == 3 * 24


def test_predict_value_lower_upper_nonnegative(
    fitted_artifact: Path, tmp_path: Path
) -> None:
    from_dt = datetime(2026, 2, 1, 0, 0, 0)
    to_dt = from_dt + timedelta(hours=6)
    cfg = PredictConfig(
        artifacts_dir=fitted_artifact,
        output_dir=tmp_path / "predictions",
        model_id="baseline_v1",
        from_dt=from_dt,
        to_dt=to_dt,
        horizon="day",
        granularity="hour",
        stop_ids=[1, 2],
    )
    df = pq.read_table(predict(cfg)).to_pandas()
    assert (df["value"] >= 0).all()
    assert (df["lower"] >= 0).all()
    assert (df["upper"] >= 0).all()


def test_predict_filename_contains_model_id_and_date(
    fitted_artifact: Path, tmp_path: Path
) -> None:
    from_dt = datetime(2026, 2, 1, 0, 0, 0)
    to_dt = from_dt + timedelta(hours=2)
    cfg = PredictConfig(
        artifacts_dir=fitted_artifact,
        output_dir=tmp_path / "predictions",
        model_id="baseline_v1",
        from_dt=from_dt,
        to_dt=to_dt,
        horizon="day",
        granularity="hour",
        stop_ids=[1],
    )
    out_path = predict(cfg)
    assert "baseline_v1" in out_path.name
    assert "2026-02-01" in out_path.name


def test_predict_uses_active_model_when_model_id_is_none(
    fitted_artifact: Path, tmp_path: Path
) -> None:
    from_dt = datetime(2026, 2, 1, 0, 0, 0)
    to_dt = from_dt + timedelta(hours=24)
    cfg = PredictConfig(
        artifacts_dir=fitted_artifact,
        output_dir=tmp_path / "predictions",
        model_id=None,
        from_dt=from_dt,
        to_dt=to_dt,
        horizon="day",
        granularity="hour",
        stop_ids=[1],
    )
    df = pq.read_table(predict(cfg)).to_pandas()
    assert (df["model_id"] == "baseline_v1").all()


def test_predict_raises_for_missing_artifact(tmp_path: Path) -> None:
    cfg = PredictConfig(
        artifacts_dir=tmp_path / "empty_artifacts",
        output_dir=tmp_path / "predictions",
        model_id="ghost_v1",
        from_dt=datetime(2026, 2, 1),
        to_dt=datetime(2026, 2, 2),
        horizon="day",
        granularity="hour",
        stop_ids=[1],
    )
    with pytest.raises(FileNotFoundError):
        predict(cfg)
