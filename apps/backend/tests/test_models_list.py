"""Tests for models list API endpoint (T-021)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.forecast.loader import reset_loader_cache
from app.main import create_app


def _write_meta(art_dir: Path, model_id: str, kind: str = "baseline") -> None:
    """Helper: write a minimal valid meta.json for one artifact."""
    art_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "model_id": model_id,
        "kind": kind,
        "version": "v0.1.0",
        "trained_at": "2026-09-22T20:00:00+00:00",
        "metrics": {"rmsle": 0.28},
        "files": {"model": "model.pkl"},
    }
    (art_dir / "meta.json").write_text(json.dumps(meta))
    # The endpoint must not need a real model file, but tests should not crash
    # if it's missing because the loader validates meta.json only.
    (art_dir / "model.pkl").write_bytes(b"fake")


@pytest.fixture()
def client_with_two_artifacts(tmp_path: Path) -> TestClient:
    """Two artifacts (baseline_v1, xgboost_v1), baseline_v1 active."""
    artifacts = tmp_path / "artifacts"
    _write_meta(artifacts / "baseline_v1", "baseline_v1", kind="baseline")
    _write_meta(artifacts / "xgboost_v1", "xgboost_v1", kind="xgboost")
    (artifacts / "active.json").write_text(json.dumps({"model_id": "baseline_v1"}))

    reset_loader_cache()
    app = create_app()
    from app.api import models as models_mod
    from app.forecast.loader import ArtifactLoader

    test_loader = ArtifactLoader(artifacts_dir=artifacts)
    app.dependency_overrides[models_mod.get_loader] = lambda: test_loader
    return TestClient(app)


@pytest.fixture()
def client_with_no_artifacts(tmp_path: Path) -> TestClient:
    """No artifacts dir at all."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    reset_loader_cache()
    app = create_app()
    from app.api import models as models_mod
    from app.forecast.loader import ArtifactLoader

    test_loader = ArtifactLoader(artifacts_dir=artifacts)
    app.dependency_overrides[models_mod.get_loader] = lambda: test_loader
    return TestClient(app)


def test_list_models_returns_all_artifacts(client_with_two_artifacts: TestClient) -> None:
    response = client_with_two_artifacts.get("/api/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert "models" in body
    assert "active_model_id" in body
    assert body["active_model_id"] == "baseline_v1"

    model_ids = {m["model_id"] for m in body["models"]}
    assert model_ids == {"baseline_v1", "xgboost_v1"}


def test_list_models_marks_active_flag(client_with_two_artifacts: TestClient) -> None:
    response = client_with_two_artifacts.get("/api/v1/models")
    body = response.json()

    by_id = {m["model_id"]: m for m in body["models"]}
    assert by_id["baseline_v1"]["is_active"] is True
    assert by_id["xgboost_v1"]["is_active"] is False


def test_list_models_includes_metadata(client_with_two_artifacts: TestClient) -> None:
    response = client_with_two_artifacts.get("/api/v1/models")
    body = response.json()

    by_id = {m["model_id"]: m for m in body["models"]}
    bl = by_id["baseline_v1"]
    assert bl["kind"] == "baseline"
    assert bl["version"] == "v0.1.0"
    assert "trained_at" in bl
    assert bl["metrics"] == {"rmsle": 0.28}


def test_list_models_filter_active_only(client_with_two_artifacts: TestClient) -> None:
    response = client_with_two_artifacts.get("/api/v1/models", params={"active_only": "true"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["models"]) == 1
    assert body["models"][0]["model_id"] == "baseline_v1"


def test_list_models_returns_empty_when_no_artifacts(client_with_no_artifacts: TestClient) -> None:
    response = client_with_no_artifacts.get("/api/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert body["models"] == []
    # No active.json → active_model_id is null
    assert body["active_model_id"] is None


def test_list_models_skips_invalid_meta(tmp_path: Path) -> None:
    """Invalid meta.json entries must NOT crash the endpoint; they're skipped."""
    artifacts = tmp_path / "artifacts"

    _write_meta(artifacts / "baseline_v1", "baseline_v1")

    # broken_v1 has invalid meta (missing required fields)
    (artifacts / "broken_v1").mkdir(parents=True)
    (artifacts / "broken_v1" / "meta.json").write_text(
        json.dumps({"model_id": "broken_v1"})  # missing required fields
    )

    (artifacts / "active.json").write_text(json.dumps({"model_id": "baseline_v1"}))

    reset_loader_cache()
    app = create_app()
    from app.api import models as models_mod
    from app.forecast.loader import ArtifactLoader

    test_loader = ArtifactLoader(artifacts_dir=artifacts)
    app.dependency_overrides[models_mod.get_loader] = lambda: test_loader
    client = TestClient(app)

    response = client.get("/api/v1/models")
    assert response.status_code == 200
    body = response.json()
    model_ids = {m["model_id"] for m in body["models"]}
    # Invalid meta must be skipped, only baseline_v1 returned
    assert model_ids == {"baseline_v1"}
