"""Models registry API endpoints.

Lists all known ML artifacts on disk and exposes the currently active one.

The endpoint is read-only — model activation is intentionally kept out of
the HTTP API for the MVP (it happens via `make activate-model-id=...`,
see `scripts/activate.py`). A future T-NNN ticket can add a POST
`/api/v1/models/{id}/activate` endpoint if the UI needs it.

References:
- T-021 (this ticket)
- `.clinerules/10-ml-as-scripts.md` (artifact registry layout)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.forecast.loader import ArtifactLoader, ModelArtifact, get_loader

router = APIRouter(prefix="/api/v1", tags=["models"])


def _artifact_to_dict(artifact: ModelArtifact, *, is_active: bool) -> dict[str, Any]:
    """Serialize a ModelArtifact for the public API response.

    Kept as a free function (not a Pydantic model) for MVP simplicity.
    When the schema stabilizes we can promote it to `app.schemas.models`.
    """
    return {
        "model_id": artifact.model_id,
        "kind": artifact.kind,
        "version": artifact.version,
        "trained_at": artifact.trained_at,
        "git_commit": artifact.git_commit,
        "horizons": list(artifact.horizons),
        "granularities": list(artifact.granularities),
        "metrics": dict(artifact.metrics),
        "is_active": is_active,
    }


@router.get("/models", summary="List all known ML artifacts")
def list_models(
    active_only: bool = Query(
        default=False,
        description="If true, return only the currently active model.",
    ),
    loader: ArtifactLoader = Depends(get_loader),
) -> dict[str, Any]:
    """Return metadata of every valid ML artifact on disk.

    The `is_active` flag tells the UI which one is currently serving
    predictions. If `active.json` is missing or points to a broken
    artifact, `active_model_id` is null and every model reports
    `is_active=false` — the endpoint must still return successfully.
    """
    active_id = loader.get_active_id()
    artifacts = loader.list_all()

    if active_only:
        artifacts = [a for a in artifacts if a.model_id == active_id]

    models = [
        _artifact_to_dict(a, is_active=(a.model_id == active_id)) for a in artifacts
    ]

    return {
        "models": models,
        "active_model_id": active_id,
        "count": len(models),
    }


__all__ = ["list_models", "router"]
