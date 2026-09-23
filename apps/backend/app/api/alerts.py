"""Dispatcher overload alerts API (T-131).

`GET /api/v1/insights/alerts?window_min=30` returns sorted overload alerts
across all in-scope stops for the next `window_min` minutes.

The endpoint reuses `app.data.transit.compute_eta_predictions` (T-127) +
`app.forecast.load.compute_load_pct` (T-128) to compute per-stop ETAs and
adapts them via `app.insights.alerts.find_overload_alerts` into actionable
`OverloadAlert` records.

`s`cope of stops is global for now (all four stops registered in
`app.data.transit.STOP_ROUTES`). When real data lands (T-026 RealSource),
this becomes geography/area-scoped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query

from app.data.transit import (
    STOP_ROUTES,
    RouteRef,
    compute_eta_predictions,
)
from app.forecast.loader import ArtifactLoader, get_loader
from app.insights.alerts import (
    DEFAULT_WINDOW_MIN,
    MAX_WINDOW_MIN,
    OverloadAlert,
    find_overload_alerts,
)
from app.schemas.alerts import OverloadAlert as SchemaOverloadAlert
from app.schemas.alerts import OverloadAlertsResponse
from app.schemas.eta import ETAPrediction

if TYPE_CHECKING:
    from transit_ai.models.base import Predictor


router = APIRouter(prefix="/api/v1", tags=["insights"])


def _route_meta_dict() -> dict[int, RouteRef]:
    """Flatten `STOP_ROUTES` to ``route_id -> RouteRef`` for `find_overload_alerts`."""
    meta: dict[int, RouteRef] = {}
    for routes in STOP_ROUTES.values():
        for r in routes:
            meta.setdefault(r.id, r)
    return meta


def _eta_by_stop(
    stop_ids: list[int],
    *,
    predictor: Predictor,
) -> dict[int, list[ETAPrediction]]:
    """For each stop in ``stop_ids`` compute its next tram predictions."""
    out: dict[int, list[ETAPrediction]] = {}
    for stop_id in stop_ids:
        out[stop_id] = compute_eta_predictions(
            stop_id=stop_id,
            n=5,
            predictor=predictor,
        )
    return out


@router.get("/insights/alerts", response_model=OverloadAlertsResponse)
def get_overload_alerts(
    window_min: int = Query(
        DEFAULT_WINDOW_MIN,
        ge=1,
        le=MAX_WINDOW_MIN,
        description=(
            "Look-ahead horizon in minutes. Defaults to 30 (current peak commute). "
            f"Hard cap {MAX_WINDOW_MIN} (4 hours) for dispatcher UI sanity."
        ),
    ),
    loader: ArtifactLoader = Depends(get_loader),
) -> OverloadAlertsResponse:
    """Return sorted overload alerts for the upcoming ``window_min`` minutes."""
    from transit_ai.models.baseline import BaselineMean

    artifact = loader.get_active()
    model_path = artifact.path / artifact.files["model"]
    if artifact.kind == "baseline":
        predictor: Predictor = BaselineMean.load(model_path)
    else:
        # XGBoost/GRU/Hybrid (T-028..T-030) plug in here once they ship.
        predictor = BaselineMean.load(model_path)

    stop_ids = list(STOP_ROUTES.keys())
    eta_by_stop = _eta_by_stop(stop_ids, predictor=predictor)

    domain_alerts: list[OverloadAlert] = find_overload_alerts(
        eta_by_route=eta_by_stop,
        route_meta=_route_meta_dict(),
        window_min=window_min,
        stop_routes_in_scope=stop_ids,
    )

    schema_alerts = [SchemaOverloadAlert(**a.__dict__) for a in domain_alerts]

    return OverloadAlertsResponse(
        generated_at=datetime.now(UTC),
        window_min=window_min,
        alerts=schema_alerts,
    )


__all__ = ["router"]
