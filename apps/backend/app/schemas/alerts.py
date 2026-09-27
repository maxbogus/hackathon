"""Pydantic schemas for the dispatcher overload alerts endpoint (T-131).

Mirrored in TypeScript via `apps/frontend/src/generated/api.schemas.ts`
once `make api-gen && make fe-gen` is run.

Severity thresholds mirror `app.insights.alerts.SEVERITY_*` constants — the
overlap is intentional: AC p.3 of T-131 documents them in one place, and
the OpenAPI schema surfaces them as machine-readable enum.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.insights.alerts import (
    HORIZONS,
    MAX_LOAD_PCT,
    MAX_WINDOW_MIN,
    SEVERITY_INFO_MIN,
)

# Severity literal — surfaced as enum in OpenAPI.
SeverityLevel = Literal["info", "warning", "critical"]


class OverloadAlert(BaseModel):
    """One actionable overload prediction for the dispatcher UI."""

    model_config = ConfigDict(extra="forbid")

    stop_id: int = Field(
        description="Numeric stop id (mirrors app.data.transit.STOP_ROUTES)."
    )
    route_id: int = Field(description="Numeric route id.")
    route_name: str = Field(
        description="Human-readable route label (e.g. '7', 'A', 'T1').",
    )
    predicted_load_pct: float = Field(
        ge=SEVERITY_INFO_MIN,
        le=MAX_LOAD_PCT,
        description=(
            "Predicted load as % of tram capacity. Always >= 75 (the alert "
            "threshold) and <= 150 (the MAX_LOAD_PCT clamp). Server-side "
            "filtering has already removed sub-threshold predictions."
        ),
    )
    time_to_overload_min: int = Field(
        ge=0,
        le=MAX_WINDOW_MIN,
        description=(
            "ETA in minutes of the specific tram this alert refers to "
            "(minutes until the tram leaves this stop). Each alert card in "
            "the dispatcher UI is rendered against its own time-to-overload. "
            f"Hard cap {MAX_WINDOW_MIN} (=24h) mirrors backend's MAX_WINDOW_MIN."
        ),
    )
    severity: SeverityLevel = Field(
        description=(
            "Bucketed risk level. info in [75,90), warning in [90,110), critical >=110."
        ),
    )


class OverloadAlertsResponse(BaseModel):
    """Response body for `GET /api/v1/insights/alerts`."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime = Field(
        description="Server-side UTC timestamp of the alert scan."
    )
    window_min: int = Field(
        ge=1,
        le=MAX_WINDOW_MIN,
        description="Look-ahead horizon used for this scan (minutes).",
    )
    horizon: str = Field(
        default="day",
        description=(
            f"Forecast horizon used to score alerts. One of {HORIZONS}."
        ),
    )
    alerts: list[OverloadAlert] = Field(
        default_factory=list,
        description=(
            "Sorted alerts: critical first, then warning, then info. "
            "Within a severity, by time_to_overload_min ascending."
        ),
    )


__all__ = [
    "OverloadAlert",
    "OverloadAlertsResponse",
    "SeverityLevel",
]
