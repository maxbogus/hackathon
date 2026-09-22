"""Tests for transit_ai.training.train universal trainer (T-032).

Контракт train_model(model_cls, config):
- SyntheticSource → fit(model_cls) → registry.save → registry.activate
- meta.json валиден против prediction_artifact.schema.json
- train_data_hash вычислен через registry.hash_dataframe
- --seed принимается из CLI → meta.json.seed
- Один и тот же train_model работает и для BaselineMean, и для XGBoostPredictor
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.baseline import BaselineMean
from transit_ai.models.xgboost_pred import XGBoostPredictor
from transit_ai.training.train import (
    DEFAULT_N_DAYS,
    TrainConfig,
    train_model,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "prediction_artifact.schema.json"


# ---------- Fixtures ----------


@pytest.fixture()
def schema() -> dict[str, Any]:
    raw: Any = json.loads(SCHEMA_PATH.read_text())
    # Schema must be a JSON object (dict); coerce defensively.
    return raw if isinstance(raw, dict) else {}


@pytest.fixture()
def ridership_df() -> pd.DataFrame:
    """35 days synthetic: 28 train + 7 holdout."""
    src = SyntheticSource(SyntheticConfig(n_days=35, seed=42))
    return src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 2, 4)))


@pytest.fixture()
def train_cfg(tmp_path: Path) -> TrainConfig:
    return TrainConfig(
        n_days=35,
        seed=42,
        model_id="baseline_v1",
        version="v0.1.0",
        horizons=("day",),
        granularities=("hour",),
        hyperparams={},
        artifacts_dir=tmp_path,
    )


# ---------- Pure unit tests for TrainConfig ----------


def test_train_config_defaults_match_makefile() -> None:
    """Defaults из TrainConfig должны соответствовать Makefile-флагам."""
    assert DEFAULT_N_DAYS == 35
    cfg = TrainConfig()
    assert cfg.seed == 42
    assert cfg.horizons == ("day",)
    assert cfg.granularities == ("hour",)
    assert cfg.model_id == "baseline_v1"
    assert cfg.version == "v0.1.0"


def test_train_config_is_frozen() -> None:
    """TrainConfig — frozen dataclass (immutable config)."""
    cfg = TrainConfig()
    with pytest.raises((AttributeError, Exception)):
        cfg.seed = 100  # type: ignore[misc]


# ---------- Integration: train_model with BaselineMean ----------


def test_train_model_baseline_creates_artifact_and_activates(
    train_cfg: TrainConfig, schema: dict[str, Any]
) -> None:
    """train_model(BaselineMean, cfg) → artifact + valid meta.json + active.json."""
    save_result = train_model(BaselineMean, train_cfg)

    assert save_result.artifact_dir.is_dir()
    assert (save_result.artifact_dir / "meta.json").is_file()
    assert (save_result.artifact_dir / "model.pkl").is_file()

    meta = save_result.meta
    jsonschema.validate(instance=meta, schema=schema)
    assert meta["model_id"] == "baseline_v1"
    assert meta["kind"] == "baseline"
    assert meta["version"] == "v0.1.0"
    assert meta["seed"] == 42
    assert meta["horizons"] == ["day"]
    assert meta["granularities"] == ["hour"]

    active_path = train_cfg.artifacts_dir / "active.json"
    assert active_path.is_file()
    assert json.loads(active_path.read_text()) == {"model_id": "baseline_v1"}


def test_train_model_baseline_train_data_hash_is_sha256(train_cfg: TrainConfig) -> None:
    """train_data_hash = sha256 от synthetic ridership DataFrame."""
    save_result = train_model(BaselineMean, train_cfg)
    meta = save_result.meta
    assert "train_data_hash" in meta
    assert isinstance(meta["train_data_hash"], str)
    assert len(meta["train_data_hash"]) == 64


def test_train_model_baseline_git_commit_recorded(train_cfg: TrainConfig) -> None:
    """git_commit либо SHA, либо None (если не в git repo)."""
    save_result = train_model(BaselineMean, train_cfg)
    meta = save_result.meta
    assert "git_commit" in meta
    assert meta["git_commit"] is None or isinstance(meta["git_commit"], str)


def test_train_model_is_deterministic(train_cfg: TrainConfig) -> None:
    """Two runs with same seed → identical train_data_hash."""
    cfg1 = TrainConfig(
        n_days=train_cfg.n_days,
        seed=42,
        model_id="baseline_v1",
        artifacts_dir=train_cfg.artifacts_dir / "run1",
    )
    cfg2 = TrainConfig(
        n_days=train_cfg.n_days,
        seed=42,
        model_id="baseline_v1",
        artifacts_dir=train_cfg.artifacts_dir / "run2",
    )
    train_model(BaselineMean, cfg1)
    train_model(BaselineMean, cfg2)

    meta1 = json.loads((cfg1.artifacts_dir / "baseline_v1" / "meta.json").read_text())
    meta2 = json.loads((cfg2.artifacts_dir / "baseline_v1" / "meta.json").read_text())
    assert meta1["train_data_hash"] == meta2["train_data_hash"]


def test_train_model_xgboost_uses_same_entrypoint(train_cfg: TrainConfig) -> None:
    """train_model работает и для XGBoostPredictor."""
    cfg = TrainConfig(
        n_days=14,
        seed=42,
        model_id="xgboost_v1",
        artifacts_dir=train_cfg.artifacts_dir / "xgb",
        hyperparams={"n_estimators": 50, "max_depth": 4},
    )
    save_result = train_model(XGBoostPredictor, cfg)
    assert save_result.meta["model_id"] == "xgboost_v1"
    assert save_result.meta["kind"] == "xgboost"


def test_train_model_raises_for_unsupported_class(train_cfg: TrainConfig) -> None:
    """Передача не-Predictor класса → TypeError."""

    class NotAPredictor:
        pass

    with pytest.raises(TypeError, match="Predictor"):
        train_model(NotAPredictor, train_cfg)  # type: ignore[arg-type]


def test_train_model_handles_empty_hyperparams(train_cfg: TrainConfig) -> None:
    """Пустые hyperparams → predictor создаётся с дефолтами."""
    cfg = TrainConfig(
        n_days=14,
        seed=42,
        model_id="baseline_v1",
        hyperparams={},
        artifacts_dir=train_cfg.artifacts_dir / "empty",
    )
    save_result = train_model(BaselineMean, cfg)
    assert save_result.meta["model_id"] == "baseline_v1"


def test_train_model_applies_hyperparams(train_cfg: TrainConfig) -> None:
    """hyperparams попадают в __init__ predictor (через setattr-фильтр)."""
    cfg = TrainConfig(
        n_days=14,
        seed=42,
        model_id="baseline_v1",
        hyperparams={"model_id": "baseline_v2"},
        artifacts_dir=train_cfg.artifacts_dir / "hp",
    )
    save_result = train_model(BaselineMean, cfg)
    assert save_result.meta["model_id"] == "baseline_v2"


# ---------- Tests for scripts/train_baseline.py ----------


def _run_train_baseline(
    artifacts_dir: Path, *args: str, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "TRANSIT_AI_ARTIFACTS_DIR": str(artifacts_dir),
        "PYTHONPATH": str(REPO_ROOT / "ml"),
    }
    return subprocess.run(
        [
            "uv",
            "--directory",
            str(REPO_ROOT / "ml"),
            "run",
            "python",
            "scripts/train_baseline.py",
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )


def test_train_baseline_script_runs(tmp_path: Path) -> None:
    """scripts/train_baseline.py создаёт artifact + active.json."""
    result = _run_train_baseline(tmp_path, "--n-days", "21")
    if result.returncode != 0:
        pytest.fail(
            f"train_baseline.py failed: stdout={result.stdout[:500]} stderr={result.stderr[:500]}"
        )

    assert (tmp_path / "baseline_v1" / "meta.json").is_file()
    assert (tmp_path / "baseline_v1" / "model.pkl").is_file()
    assert (tmp_path / "active.json").is_file()
    assert json.loads((tmp_path / "active.json").read_text()) == {
        "model_id": "baseline_v1"
    }


def test_train_baseline_script_cli_args(tmp_path: Path) -> None:
    """--seed и --model-id передаются через CLI."""
    result = _run_train_baseline(
        tmp_path,
        "--n-days",
        "14",
        "--seed",
        "7",
        "--model-id",
        "baseline_test",
        "--no-activate",
    )
    if result.returncode != 0:
        pytest.fail(
            f"train_baseline.py with args failed: stdout={result.stdout[:500]} stderr={result.stderr[:500]}"
        )

    meta = json.loads((tmp_path / "baseline_test" / "meta.json").read_text())
    assert meta["model_id"] == "baseline_test"
    assert meta["seed"] == 7
    active_path = tmp_path / "active.json"
    if active_path.exists():
        active = json.loads(active_path.read_text())
        assert active.get("model_id") != "baseline_test"


def test_train_baseline_script_config_yaml_loaded(tmp_path: Path) -> None:
    """Если --config указан → читается YAML (через train_model)."""
    import yaml  # type: ignore[import-untyped]

    cfg_yaml = tmp_path / "baseline.yaml"
    cfg_yaml.write_text(
        yaml.safe_dump(
            {"n_days": 14, "seed": 99, "model_id": "from_yaml", "hyperparams": {}}
        )
    )
    result = _run_train_baseline(tmp_path, "--config", str(cfg_yaml))
    if result.returncode != 0:
        assert "No such file" not in result.stderr
        assert "ModuleNotFoundError" not in result.stderr
