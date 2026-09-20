"""Tests for apps/backend/forecast/loader.py — ArtifactLoader.

Contract: docs/schemas/prediction_artifact.schema.json
Artifacts layout: ml/artifacts/<model_id>/{meta.json, model.pkl, preprocessor.pkl}
Active model:      ml/artifacts/active.json → {"model_id": "baseline_v1"}
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.forecast.loader import (
    ActiveArtifactNotFoundError,
    ArtifactLoader,
    ArtifactNotFoundError,
    ArtifactValidationError,
)

# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture()
def artifacts_root(tmp_path: Path) -> Path:
    """Build a fake ml/artifacts/ tree with one valid artifact."""
    root = tmp_path / "artifacts"
    (root / "baseline_v1").mkdir(parents=True)

    meta = {
        "model_id": "baseline_v1",
        "kind": "baseline",
        "version": "v0.1.0",
        "trained_at": "2026-09-20T12:00:00Z",
        "metrics": {"rmsle": 0.28},
        "files": {"model": "model.pkl"},
    }
    (root / "baseline_v1" / "meta.json").write_text(json.dumps(meta))
    (root / "baseline_v1" / "model.pkl").write_bytes(b"fake-model-bytes")

    (root / "active.json").write_text(json.dumps({"model_id": "baseline_v1"}))
    return root


# ----------------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------------


def test_load_returns_meta_for_valid_artifact(artifacts_root: Path) -> None:
    loader = ArtifactLoader(artifacts_root)
    artifact = loader.load("baseline_v1")

    assert artifact.model_id == "baseline_v1"
    assert artifact.kind == "baseline"
    assert artifact.version == "v0.1.0"
    assert artifact.metrics["rmsle"] == 0.28
    assert artifact.files["model"] == "model.pkl"


def test_get_active_returns_active_artifact(artifacts_root: Path) -> None:
    loader = ArtifactLoader(artifacts_root)
    artifact = loader.get_active()

    assert artifact.model_id == "baseline_v1"


# ----------------------------------------------------------------------------
# Error path
# ----------------------------------------------------------------------------


def test_load_raises_when_meta_missing(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    (root / "missing_v1").mkdir(parents=True)
    loader = ArtifactLoader(root)

    with pytest.raises(ArtifactNotFoundError) as exc_info:
        loader.load("missing_v1")
    assert "missing_v1" in str(exc_info.value)


def test_load_raises_validation_error_on_invalid_meta(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    (root / "broken_v1").mkdir(parents=True)
    (root / "broken_v1" / "meta.json").write_text(
        json.dumps({"model_id": "broken_v1"})  # missing required fields
    )
    loader = ArtifactLoader(root)

    with pytest.raises(ArtifactValidationError) as exc_info:
        loader.load("broken_v1")
    # Must wrap jsonschema.ValidationError, not just re-raise it
    assert "broken_v1" in str(exc_info.value)


def test_get_active_raises_when_active_pointer_missing(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    loader = ArtifactLoader(root)

    with pytest.raises(ActiveArtifactNotFoundError):
        loader.get_active()


def test_get_active_raises_when_active_points_to_missing_model(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "active.json").write_text(json.dumps({"model_id": "ghost_v1"}))
    loader = ArtifactLoader(root)

    with pytest.raises(ArtifactNotFoundError) as exc_info:
        loader.get_active()
    assert "ghost_v1" in str(exc_info.value)
