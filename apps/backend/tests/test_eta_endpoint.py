"""Tests for /api/v1/predictions/eta endpoint (T-127).

Contract alignment:
- Frontend `apps/frontend/src/lib/recommend.ts` defines `ETAPrediction`:
    { route_id, route_name, eta_min, predicted_load_pct, model_id }
- This endpoint must return the SAME shape so Orval-generated hooks
  (apps/frontend/src/generated/api.ts) are drop-in for the UI.

Algorithm:
- Endpoint reads the active ML artifact via ArtifactLoader.
- Calls `compute_eta_predictions(stop_id, n, predictor)` from app.data.transit
  which predicts hourly ridership for [now, now+60min], splits into N buckets,
  and assigns ETA/load_pct/route_id/route_name from STOP_ROUTES lookup.

STOP_ROUTES is hardcoded to match `apps/frontend/src/mocks/stops.json` so
switching `VITE_USE_MOCK=0 ↔ 1` produces the same visible demo for the jury.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.forecast.loader import ArtifactLoader, reset_loader_cache
from app.main import create_app


def _build_active_baseline_artifact(artifacts_dir: Path) -> None:
    """Fit a tiny BaselineMean on synthetic data, pickle it, write meta+active."""
    from transit_ai.data.base import DateRange
    from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
    from transit_ai.models.baseline import BaselineMean

    art_dir = artifacts_dir / "baseline_v1"
    art_dir.mkdir(parents=True, exist_ok=True)

    src = SyntheticSource(SyntheticConfig(n_days=10, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 10)))
    m = BaselineMean(model_id="baseline_v1")
    m.fit(rid)

    with (art_dir / "model.pkl").open("wb") as f:
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
    (artifacts_dir / "active.json").write_text(json.dumps({"model_id": "baseline_v1"}))


@pytest.fixture()
def client_with_baseline(tmp_path: Path) -> TestClient:
    """Build a fake ml/artifacts/ tree with one baseline_v1 artifact, return TestClient."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _build_active_baseline_artifact(artifacts)

    reset_loader_cache()
    app = create_app()

    from app.api import predictions as predictions_mod

    test_loader = ArtifactLoader(artifacts_dir=artifacts)
    app.dependency_overrides[predictions_mod.get_loader] = lambda: test_loader
    return TestClient(app)


@pytest.fixture()
def client_with_no_artifact(tmp_path: Path) -> TestClient:
    """TestClient pointing at an empty artifacts dir → 503 path."""
    empty = tmp_path / "artifacts"
    empty.mkdir()
    (empty / "active.json").unlink(missing_ok=True)

    reset_loader_cache()
    app = create_app()
    from app.api import predictions as predictions_mod

    test_loader = ArtifactLoader(artifacts_dir=empty)
    app.dependency_overrides[predictions_mod.get_loader] = lambda: test_loader
    return TestClient(app)


# ---- Happy path ----


def test_eta_returns_default_n3_trams_for_known_stop(
    client_with_baseline: TestClient,
) -> None:
    """stop_id=1 (Белорусская) → 3 trams by default."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stop_id"] == 1
    assert body["n_requested"] == 3
    assert len(body["trams"]) == 3
    assert body["horizon_minutes"] == 60


def test_eta_respects_n_parameter(client_with_baseline: TestClient) -> None:
    """n=5 → 5 trams."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 1, "n": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["n_requested"] == 5
    assert len(body["trams"]) == 5


def test_eta_response_schema_has_all_fields(client_with_baseline: TestClient) -> None:
    """Each tram must carry every field expected by frontend `ETAPrediction`."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 1}
    )
    body = response.json()
    first = body["trams"][0]
    assert set(first.keys()) == {
        "route_id",
        "route_name",
        "eta_min",
        "predicted_load_pct",
        "model_id",
    }
    assert isinstance(first["route_id"], int)
    assert isinstance(first["route_name"], str)
    assert isinstance(first["eta_min"], int)
    assert isinstance(first["predicted_load_pct"], (int, float))
    assert first["model_id"] == "baseline_v1"


def test_eta_eta_min_monotonic_increasing(client_with_baseline: TestClient) -> None:
    """Trams are sorted by arrival time — first is closest."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 1}
    )
    body = response.json()
    etas = [t["eta_min"] for t in body["trams"]]
    assert etas == sorted(etas)
    assert etas[0] >= 0
    assert etas[-1] <= 60


def test_eta_load_pct_within_0_100(client_with_baseline: TestClient) -> None:
    """load_pct is a percentage — must be clamped to [0, 100]."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 4}
    )
    body = response.json()
    for t in body["trams"]:
        assert 0.0 <= t["predicted_load_pct"] <= 100.0


# ---- Edge cases ----


def test_eta_n_clamped_to_max_5(client_with_baseline: TestClient) -> None:
    """n=10 → 5 (max trams the UI can render in one card stack)."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 1, "n": 10}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["trams"]) == 5
    assert body["n_requested"] == 5  # clamped, but reported honestly


def test_eta_n_min_is_1(client_with_baseline: TestClient) -> None:
    """n=0 → 422 (Pydantic validation: ge=1)."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 1, "n": 0}
    )
    assert response.status_code == 422


def test_eta_unknown_stop_returns_empty_trams(client_with_baseline: TestClient) -> None:
    """stop_id=9999 not in STOP_ROUTES → empty list (UI shows 'no data')."""
    response = client_with_baseline.get(
        "/api/v1/predictions/eta", params={"stop_id": 9999}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stop_id"] == 9999
    assert body["trams"] == []


# ---- Error path ----


def test_eta_returns_503_when_no_active_model(
    client_with_no_artifact: TestClient,
) -> None:
    """If active.json missing, endpoint surfaces 503 (consistent with /models/active)."""
    response = client_with_no_artifact.get(
        "/api/v1/predictions/eta", params={"stop_id": 1}
    )
    assert response.status_code == 503


# ---- CORS ----


def test_eta_cors_headers_present(client_with_baseline: TestClient) -> None:
    """CORS preflight from localhost:5173 must succeed (frontend dev port)."""
    response = client_with_baseline.options(
        "/api/v1/predictions/eta",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert "access-control-allow-origin" in {k.lower() for k in response.headers}
