"""Pydantic schemas for /api/v1/predictions/eta endpoint (T-127).

These shapes are duplicated in TypeScript at
`apps/frontend/src/lib/recommend.ts` (interface ETAPrediction).
Keep them in sync — backend-first contract → `make api-gen` → Orval → frontend.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ETAPrediction(BaseModel):
    """One tram approaching a stop.

    Mirrors the TypeScript `ETAPrediction` interface in
    `apps/frontend/src/lib/recommend.ts` — do not rename fields without
    regenerating `apps/frontend/src/generated/api.ts`.
    """

    model_config = ConfigDict(extra="forbid")

    route_id: int = Field(description="Numeric id of the route (e.g. 7).")
    route_name: str = Field(
        description="Human-readable label (e.g. '7', 'А'). May equal route_id "
        "as a string for numeric-only routes.",
    )
    eta_min: int = Field(
        ge=0,
        le=60,
        description="Minutes until arrival. 0 = already at the stop / leaving now.",
    )
    predicted_load_pct: float = Field(
        ge=0.0,
        le=150.0,
        description=(
            "Predicted load as % of tram capacity. Clamped to [0, 150] — "
            "values >100 mean the tram is predicted to be overloaded "
            "(darkred on the colour scale)."
        ),
    )
    model_id: str = Field(description="Id of the model that produced this prediction.")


class ETAResponse(BaseModel):
    """Response body of GET /api/v1/predictions/eta."""

    model_config = ConfigDict(extra="forbid")

    stop_id: int = Field(description="Echo of the request's stop_id.")
    generated_at: datetime = Field(
        description="Server time when the response was assembled (ISO 8601).",
    )
    horizon_minutes: int = Field(
        default=60,
        description="How far into the future predictions were made.",
    )
    n_requested: int = Field(
        ge=1,
        le=5,
        description="Number of trams requested (clamped to [1, 5]).",
    )
    trams: list[ETAPrediction] = Field(
        default_factory=list,
        description="Sorted by eta_min ascending. Empty list = no data.",
    )


__all__ = ["ETAPrediction", "ETAResponse"]
