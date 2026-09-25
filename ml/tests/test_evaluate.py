"""Tests for transit_ai.training.evaluate pipeline (T-035).

Контракт evaluate:
  - load fitted Predictor from artifact (через ModelRegistry.load с dispatch по kind)
  - split ridership → последние holdout_days дней = holdout
  - для каждой строки holdout: predictor.predict() → compare с passenger_count
  - compute_metrics(rmsle, mae, mape)
  - update meta.json.metrics (через ModelRegistry.update_metrics)
  - write markdown report в docs/reports/
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.baseline import BaselineMean
from transit_ai.models.xgboost_pred import XGBoostPredictor
from transit_ai.training.evaluate import EvaluationResult, evaluate_artifact
from transit_ai.training.registry import ModelRegistry


@pytest.fixture()
def fitted_baseline() -> BaselineMean:
    src = SyntheticSource(SyntheticConfig(n_days=21, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 21)))
    m = BaselineMean(model_id="baseline_v1")
    m.fit(rid)
    return m


@pytest.fixture()
def fitted_xgb(tmp_path: Path) -> XGBoostPredictor:
    src = SyntheticSource(SyntheticConfig(n_days=21, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 21)))
    m = XGBoostPredictor(model_id="xgboost_v1")
    m.fit(rid)
    return m


@pytest.fixture()
def holdout_ridership() -> pd.DataFrame:
    """28 days synthetic — last 7 = holdout."""
    src = SyntheticSource(SyntheticConfig(n_days=28, seed=42))
    return src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 28)))


# ---------- ModelRegistry.load dispatcher ----------


def test_registry_load_dispatches_baseline(
    fitted_baseline: BaselineMean, tmp_path: Path
) -> None:
    """ModelRegistry.load('baseline_v1') → BaselineMean."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_baseline)
    loaded = reg.load("baseline_v1")
    assert isinstance(loaded, BaselineMean)
    assert loaded.model_id == "baseline_v1"
    assert loaded.fitted_


def test_registry_load_dispatches_xgboost(
    fitted_xgb: XGBoostPredictor, tmp_path: Path
) -> None:
    """ModelRegistry.load('xgboost_v1') → XGBoostPredictor."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_xgb)
    loaded = reg.load("xgboost_v1")
    assert isinstance(loaded, XGBoostPredictor)
    assert loaded.model_id == "xgboost_v1"


def test_registry_load_unknown_kind_raises(
    fitted_baseline: BaselineMean, tmp_path: Path
) -> None:
    """Unknown kind → NotImplementedError с понятным сообщением."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_baseline)
    meta_path = tmp_path / "baseline_v1" / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta["kind"] = "alien"
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(NotImplementedError, match="alien"):
        reg.load("baseline_v1")


def test_registry_load_missing_artifact_raises(tmp_path: Path) -> None:
    """load() на несуществующем model_id → FileNotFoundError."""
    reg = ModelRegistry(tmp_path)
    with pytest.raises(FileNotFoundError):
        reg.load("ghost_v1")


# ---------- evaluate_artifact pipeline ----------


def test_evaluate_artifact_returns_evaluation_result(
    fitted_baseline: BaselineMean,
    holdout_ridership: pd.DataFrame,
    tmp_path: Path,
) -> None:
    """evaluate_artifact → EvaluationResult с 3 метриками и метаданными."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_baseline)

    result = evaluate_artifact(
        model_id="baseline_v1",
        ridership_df=holdout_ridership,
        registry=reg,
        holdout_days=7,
    )
    assert isinstance(result, EvaluationResult)
    assert result.model_id == "baseline_v1"
    assert set(result.metrics.keys()) == {"rmsle", "mae", "mape", "wape", "wape_score"}
    assert result.n_points > 0
    assert result.eval_seconds >= 0.0
    assert result.holdout_start < result.holdout_end


def test_evaluate_artifact_updates_meta_json(
    fitted_baseline: BaselineMean,
    holdout_ridership: pd.DataFrame,
    tmp_path: Path,
) -> None:
    """После evaluate meta.json.metrics заполнен, git_commit сохранён."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_baseline)

    meta_path = tmp_path / "baseline_v1" / "meta.json"
    original = json.loads(meta_path.read_text())
    original_commit = original["git_commit"]
    assert original["metrics"] == {}

    evaluate_artifact(
        model_id="baseline_v1",
        ridership_df=holdout_ridership,
        registry=reg,
        holdout_days=7,
    )

    updated = json.loads(meta_path.read_text())
    assert updated["metrics"]["rmsle"] >= 0.0
    assert updated["metrics"]["mae"] >= 0.0
    assert updated["metrics"]["mape"] >= 0.0
    assert updated["git_commit"] == original_commit
    assert updated["seed"] == original["seed"]


def test_evaluate_artifact_writes_markdown_report(
    fitted_baseline: BaselineMean,
    holdout_ridership: pd.DataFrame,
    tmp_path: Path,
) -> None:
    """Markdown report создаётся и содержит RMSLE/MAE/MAPE + model_id."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_baseline)

    result = evaluate_artifact(
        model_id="baseline_v1",
        ridership_df=holdout_ridership,
        registry=reg,
        holdout_days=7,
    )

    assert result.report_path is not None
    assert result.report_path.exists()
    content = result.report_path.read_text(encoding="utf-8")
    assert "# Evaluation Report" in content
    assert "RMSLE" in content
    assert "MAE" in content
    assert "MAPE" in content
    assert "baseline_v1" in content


def test_evaluate_artifact_baseline_metrics_are_finite(
    fitted_baseline: BaselineMean,
    holdout_ridership: pd.DataFrame,
    tmp_path: Path,
) -> None:
    """Все метрики — конечные float, RMSLE разумный (sanity: < 1.5)."""
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_baseline)

    result = evaluate_artifact(
        model_id="baseline_v1",
        ridership_df=holdout_ridership,
        registry=reg,
        holdout_days=7,
    )

    for k, v in result.metrics.items():
        assert isinstance(v, float), f"{k} is {type(v)}"
        assert not math.isnan(v), f"{k} is NaN"
        assert v >= 0.0
    assert result.metrics["rmsle"] < 1.5, (
        f"baseline_v1 RMSLE {result.metrics['rmsle']:.3f} unexpectedly high"
    )
