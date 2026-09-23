"""Tests for predictions API endpoints (T-042-ish, MVP scope)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.forecast.loader import reset_loader_cache
from app.main import create_app


@pytest.fixture()
def client_with_active_artifact(tmp_path: Path) -> TestClient:
    """Build a fake artifacts tree with one baseline_v1 artifact, then return a TestClient.

    We don't call .save() because that requires a fitted Predictor; instead we
    write meta.json + a minimal model.pkl by hand.
    """
    artifacts = tmp_path / "artifacts"
    art_dir = artifacts / "baseline_v1"
    art_dir.mkdir(parents=True)

    import pickle

    from transit_ai.data.base import DateRange

    # Build & fit a tiny model so .load() works
    from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
    from transit_ai.models.baseline import BaselineMean

    src = SyntheticSource(SyntheticConfig(n_days=10, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 10)))
    m = BaselineMean(model_id="baseline_v1")
    m.fit(rid)

    with (art_dir / "model.pkl").open("wb") as f:
        # Use the SAME shape as BaselineMean.save() — a dict, not the object itself
        pickle.dump(
            {
                "model_id": m.model_id,
                "kind": m.kind,
                "table": m.table_,
                "global_table": m.global_table_,
                "fitted": m.fitted_,
            },
            f,
        )

    meta = {
        "model_id": "baseline_v1",
        "kind": "baseline",
        "version": "v0.1.0",
        "trained_at": "2026-09-20T11:00:00+00:00",
        "git_commit": "0d58869",
        "train_data_hash": "abc",
        "seed": 42,
        "horizons": ["day"],
        "granularities": ["hour"],
        "metrics": {},
        "files": {"model": "model.pkl"},
    }
    (art_dir / "meta.json").write_text(json.dumps(meta))
    (artifacts / "active.json").write_text(json.dumps({"model_id": "baseline_v1"}))

    # Reset singleton so it picks up new artifacts dir
    reset_loader_cache()
    app = create_app()

    # Override the loader to use our tmp_path
    from app.api import predictions as predictions_mod
    from app.forecast.loader import ArtifactLoader

    test_loader = ArtifactLoader(artifacts_dir=artifacts)
    app.dependency_overrides[predictions_mod.get_loader] = lambda: test_loader

    return TestClient(app)


def test_models_active_returns_baseline_info(
    client_with_active_artifact: TestClient,
) -> None:
    response = client_with_active_artifact.get("/api/v1/models/active")
    assert response.status_code == 200
    body = response.json()
    assert body["model_id"] == "baseline_v1"
    assert body["kind"] == "baseline"
    assert body["version"] == "v0.1.0"


def test_predictions_for_stop_returns_hourly_points(
    client_with_active_artifact: TestClient,
) -> None:
    start = datetime(2026, 2, 1, 7, 0, 0)
    end = datetime(2026, 2, 1, 10, 0, 0)
    response = client_with_active_artifact.get(
        "/api/v1/predictions/stop/1",
        params={"period_start": start.isoformat(), "period_end": end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stop_id"] == 1
    assert body["model_id"] == "baseline_v1"
    assert len(body["data"]) == 3  # 07:00-08:00, 08:00-09:00, 09:00-10:00
    for p in body["data"]:
        assert "value" in p
        assert "lower" in p
        assert "upper" in p
        assert p["value"] >= 0


def test_predictions_rejects_inverted_period() -> None:
    """period_start >= period_end → 400."""
    app = create_app()
    client = TestClient(app)
    response = client.get(
        "/api/v1/predictions/stop/1",
        params={
            "period_start": "2026-02-01T10:00:00",
            "period_end": "2026-02-01T07:00:00",
        },
    )
    assert response.status_code == 400


def test_models_active_returns_503_when_no_active() -> None:
    """If active.json missing, /models/active returns 503."""
    from app.forecast.loader import ArtifactLoader

    # Empty artifacts dir
    empty = Path("/tmp/empty-artifacts-test")
    empty.mkdir(exist_ok=True)
    (empty / "active.json").unlink(missing_ok=True)

    reset_loader_cache()
    app = create_app()
    test_loader = ArtifactLoader(artifacts_dir=empty)
    app.dependency_overrides = {}
    from app.api import predictions as predictions_mod

    app.dependency_overrides[predictions_mod.get_loader] = lambda: test_loader
    client = TestClient(app)
    response = client.get("/api/v1/models/active")
    assert response.status_code == 503
