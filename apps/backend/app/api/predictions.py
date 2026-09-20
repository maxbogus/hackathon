"""Predictions API endpoints.

Reads the active ML artifact via ArtifactLoader and returns predictions
for a given stop and time range.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from transit_ai.models.base import PredictionPoint
from transit_ai.models.baseline import BaselineMean

from app.forecast.loader import (
    ActiveArtifactNotFoundError,
    ArtifactLoader,
    ArtifactNotFoundError,
    get_loader,
)

router = APIRouter(prefix="/api/v1", tags=["predictions"])


def _get_predictor(loader: ArtifactLoader) -> BaselineMean:
    """Load the active artifact and reconstruct the Predictor.

    Only BaselineMean is supported here in Phase 2.1. XGBoost/GRU plug in
    via the artifact's `kind` field in T-028/T-029.
    """
    artifact = loader.get_active()
    if artifact.kind != "baseline":
        raise HTTPException(
            status_code=501,
            detail=f"Model kind {artifact.kind!r} not yet wired into predictions endpoint (only 'baseline' supported in MVP)",
        )
    model_path = artifact.path / artifact.files["model"]
    return BaselineMean.load(str(model_path))


@router.get("/predictions/stop/{stop_id}", summary="Get ridership predictions for a stop")
def get_predictions_for_stop(
    stop_id: int,
    period_start: datetime,
    period_end: datetime,
    loader: ArtifactLoader = Depends(get_loader),
) -> dict:
    """Return hourly predictions for [period_start, period_end] at one stop.

    Returns list of `{period_start, period_end, value, lower, upper, model_id}`.
    """
    if period_start >= period_end:
        raise HTTPException(status_code=400, detail="period_start must be < period_end")

    try:
        predictor = _get_predictor(loader)
    except (ArtifactNotFoundError, ActiveArtifactNotFoundError) as exc:
        raise HTTPException(status_code=503, detail=f"No active artifact: {exc}") from exc

    points: list[PredictionPoint] = predictor.predict(stop_id, period_start, period_end)

    return {
        "stop_id": stop_id,
        "model_id": predictor.model_id,
        "horizon": "day",
        "granularity": "hour",
        "data": [
            {
                "period_start": p.period_start.isoformat(),
                "period_end": p.period_end.isoformat(),
                "value": round(p.value, 2),
                "lower": round(p.lower, 2),
                "upper": round(p.upper, 2),
            }
            for p in points
        ],
    }


@router.get("/models/active", summary="Get active model info")
def get_active_model(loader: ArtifactLoader = Depends(get_loader)) -> dict:
    """Return metadata of the currently active model artifact."""
    try:
        artifact = loader.get_active()
    except (ArtifactNotFoundError, ActiveArtifactNotFoundError) as exc:
        raise HTTPException(status_code=503, detail=f"No active artifact: {exc}") from exc

    return {
        "model_id": artifact.model_id,
        "kind": artifact.kind,
        "version": artifact.version,
        "trained_at": artifact.trained_at,
        "git_commit": artifact.git_commit,
        "horizons": list(artifact.horizons),
        "granularities": list(artifact.granularities),
        "metrics": artifact.metrics,
        "path": str(artifact.path),
    }
