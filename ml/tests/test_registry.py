"""Tests for ModelRegistry (save + activate)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.baseline import BaselineMean
from transit_ai.training.registry import ModelRegistry, git_commit, hash_dataframe


@pytest.fixture()
def fitted_predictor() -> BaselineMean:
    src = SyntheticSource(SyntheticConfig(n_days=14, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 14)))
    m = BaselineMean(model_id="baseline_v1")
    m.fit(rid)
    return m


def test_registry_creates_meta_json(
    fitted_predictor: BaselineMean, tmp_path: Path
) -> None:
    reg = ModelRegistry(tmp_path)
    result = reg.save(
        fitted_predictor, version="v0.1.0", train_data_hash="abc", seed=42
    )

    meta_path = result.artifact_dir / "meta.json"
    assert meta_path.exists()
    import json

    meta = json.loads(meta_path.read_text())
    assert meta["model_id"] == "baseline_v1"
    assert meta["kind"] == "baseline"
    assert meta["version"] == "v0.1.0"


def test_registry_validates_meta_against_schema(
    fitted_predictor: BaselineMean, tmp_path: Path
) -> None:
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_predictor, version="v0.1.0")
    # If schema validation passed, save() didn't raise. Verify meta is loadable.
    meta_path = tmp_path / "baseline_v1" / "meta.json"
    meta = __import__("json").loads(meta_path.read_text())
    assert "trained_at" in meta


def test_registry_activate_writes_active_json(
    fitted_predictor: BaselineMean, tmp_path: Path
) -> None:
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_predictor)
    reg.activate("baseline_v1")

    active_path = tmp_path / "active.json"
    assert active_path.exists()
    import json

    assert json.loads(active_path.read_text()) == {"model_id": "baseline_v1"}


def test_registry_activate_rejects_missing_model(tmp_path: Path) -> None:
    reg = ModelRegistry(tmp_path)
    with pytest.raises(FileNotFoundError):
        reg.activate("ghost_v1")


def test_registry_save_then_load_predictor(
    fitted_predictor: BaselineMean, tmp_path: Path
) -> None:
    reg = ModelRegistry(tmp_path)
    reg.save(fitted_predictor)

    loaded = BaselineMean.load(str(tmp_path / "baseline_v1" / "model.pkl"))
    assert loaded.model_id == fitted_predictor.model_id
    assert loaded.fitted_


def test_registry_rejects_unfitted_predictor(tmp_path: Path) -> None:
    reg = ModelRegistry(tmp_path)
    m = BaselineMean(model_id="baseline_v1")
    m.fitted_ = False
    with pytest.raises(ValueError):
        reg.save(m)


def test_git_commit_returns_string_or_none() -> None:
    """git_commit() returns either a SHA string or None (when not in a repo)."""
    commit = git_commit()
    assert commit is None or isinstance(commit, str)
    if commit:
        assert len(commit) >= 7


def test_hash_dataframe_returns_hex_string() -> None:
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2, 3]})
    h = hash_dataframe(df)
    assert isinstance(h, str)
    assert len(h) == 64  # sha256 hex
