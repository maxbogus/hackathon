"""Predictions API endpoints.

Reads the active ML artifact via ArtifactLoader and returns predictions
for a given stop and time range.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from transit_ai.models.base import PredictionPoint
from transit_ai.models.baseline import BaselineMean

from app.data.transit import (
    HORIZON_MINUTES,
    MAX_TRAMS_PER_REQUEST,
    compute_eta_predictions,
)
from app.forecast.loader import (
    ActiveArtifactNotFoundError,
    ArtifactLoader,
    ArtifactNotFoundError,
    get_loader,
)
from app.schemas.eta import ETAResponse

router = APIRouter(prefix="/api/v1", tags=["predictions"])


def _get_predictor(loader: ArtifactLoader) -> BaselineMean:
    """Load the active artifact and reconstruct the Predictor.

    Supports baseline (T-027) and xgboost (T-028). GRU (T-029) and
    Hybrid (T-030) plug in via the same dispatcher when they land.
    """
    artifact = loader.get_active()
    model_path = artifact.path / artifact.files["model"]

    if artifact.kind == "baseline":
        return BaselineMean.load(str(model_path))
    if artifact.kind == "xgboost":
        from transit_ai.models.xgboost_pred import XGBoostPredictor

        return XGBoostPredictor.load(str(model_path))
    raise HTTPException(
        status_code=501,
        detail=f"Model kind {artifact.kind!r} not yet wired into predictions endpoint",
    )


@router.get(
    "/predictions/stop/{stop_id}", summary="Get ridership predictions for a stop"
)
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
        raise HTTPException(
            status_code=503, detail=f"No active artifact: {exc}"
        ) from exc

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


@router.get(
    "/predictions/eta",
    response_model=ETAResponse,
    summary="Get next N upcoming trams at a stop (ETA + predicted load)",
)
def get_eta_predictions(
    stop_id: int = Query(..., description="Tram stop id (1..N).", ge=1),
    n: int = Query(
        default=3,
        ge=1,
        description=(
            "Number of upcoming trams to return. Clamped to "
            f"[1, {MAX_TRAMS_PER_REQUEST}]."
        ),
    ),
    loader: ArtifactLoader = Depends(get_loader),
) -> ETAResponse:
    """Return the next N trams calling at `stop_id`.

    Used by the passenger-mode UI (T-129) to render the "next trams" cards
    with ETA + predicted load. The response shape (`ETAResponse`) is
    kept in sync with `apps/frontend/src/lib/recommend.ts`.

    Behaviour:
        - Reads the active model from `ArtifactLoader`.
        - Predicts hourly ridership over the next 60 minutes.
        - Distributes predictions across N equal-width buckets
          (see `app.data.transit.compute_eta_predictions`).
        - Returns an empty `trams` list when the stop is unknown
          (UI shows "no data").

    Errors:
        - 503: no active model artifact (consistent with /models/active).
        - 501: active model is not yet wired into the predictor dispatcher.
    """
    n_clamped = min(n, MAX_TRAMS_PER_REQUEST)

    try:
        predictor = _get_predictor(loader)
    except (ArtifactNotFoundError, ActiveArtifactNotFoundError) as exc:
        raise HTTPException(
            status_code=503, detail=f"No active artifact: {exc}"
        ) from exc

    now = datetime.now(tz=UTC)
    trams = compute_eta_predictions(
        stop_id=stop_id,
        n=n_clamped,
        predictor=predictor,
        now=now,
    )

    return ETAResponse(
        stop_id=stop_id,
        generated_at=now,
        horizon_minutes=HORIZON_MINUTES,
        n_requested=n_clamped,
        trams=trams,
    )


@router.get("/models/active", summary="Get active model info")
def get_active_model(loader: ArtifactLoader = Depends(get_loader)) -> dict:
    """Return metadata of the currently active model artifact."""
    try:
        artifact = loader.get_active()
    except (ArtifactNotFoundError, ActiveArtifactNotFoundError) as exc:
        raise HTTPException(
            status_code=503, detail=f"No active artifact: {exc}"
        ) from exc

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
