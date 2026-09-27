"""T-218: summary endpoints для PassengerMode.

GET /api/v1/predictions/load — block 'kak budet' (predictions, submission period)
GET /api/v1/historical/load  — block 'kak bylo' (actuals, last available day
                                with fallback na MAX(period_start) yesli okno pustoe)

Sm. clinerule 31.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.load_tier import compute_load_pct, compute_load_tier
from app.models import Actual, FeatureToggle, Prediction, ZeroOverride
from app.schemas.load import RouteLoadItem, RouteLoadListResponse

router = APIRouter(prefix="/api/v1", tags=["load-summary"])

DEFAULT_TRAM_CAPACITY = 150
SUBMISSION_PERIOD_START = datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC)
SUBMISSION_PERIOD_END = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


async def _default_feature_set(session: AsyncSession) -> str:
    stmt = select(FeatureToggle).where(FeatureToggle.enabled == True)
    rows = (await session.execute(stmt)).scalars().all()
    names = {r.name for r in rows}
    if {"use_poi", "use_weather", "use_events"}.issubset(names):
        return "with_all"
    if "use_poi" in names:
        return "with_poi"
    return "baseline"


async def _default_zeros_state(session: AsyncSession) -> bool:
    stmt = select(ZeroOverride).where(ZeroOverride.enabled == True)
    rows = (await session.execute(stmt)).scalars().all()
    return len(rows) > 0


@router.get(
    "/predictions/load",
    response_model=RouteLoadListResponse,
    summary="T-218: Summary predictions — avg load per route (block 'kak budet')",
)
async def get_predictions_load(
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    model_id: str | None = Query(default=None),
    feature_set: str | None = Query(default=None),
    zeros_applied: bool | None = Query(default=None),
    horizon: Literal["day", "month", "year"] = Query(default="day"),
    granularity: Literal["hour", "day", "month"] = Query(default="hour"),
    tram_capacity: int = Query(default=DEFAULT_TRAM_CAPACITY, ge=50, le=500),
    session: AsyncSession = Depends(get_db),
) -> RouteLoadListResponse:
    """Srednie boardings + load_pct za marshrutami (predictions)."""
    resolved_from = from_date or SUBMISSION_PERIOD_START
    resolved_to = to_date or SUBMISSION_PERIOD_END
    if resolved_from >= resolved_to:
        resolved_from, resolved_to = SUBMISSION_PERIOD_START, SUBMISSION_PERIOD_END

    if feature_set is None:
        feature_set = await _default_feature_set(session)
    if zeros_applied is None:
        zeros_applied = await _default_zeros_state(session)

    stmt = (
        select(
            Prediction.route_id,
            func.avg(Prediction.value).label("boardings_avg"),
            func.count(Prediction.id).label("sample_size"),
        )
        .where(
            Prediction.horizon == horizon,
            Prediction.granularity == granularity,
            Prediction.period_start >= resolved_from,
            Prediction.period_start <= resolved_to,
            Prediction.coef_weather == 1.0,
            Prediction.coef_event == 1.0,
            Prediction.coef_season == 1.0,
            Prediction.feature_set == feature_set,
            Prediction.zeros_applied == zeros_applied,
        )
        .group_by(Prediction.route_id)
        .order_by(Prediction.route_id)
    )
    if model_id is not None:
        stmt = stmt.where(Prediction.model_id == model_id)

    rows = (await session.execute(stmt)).all()

    items: list[RouteLoadItem] = []
    for route_id, boardings_avg, sample_size in rows:
        avg = float(boardings_avg or 0.0)
        pct = compute_load_pct(avg, tram_capacity)
        items.append(
            RouteLoadItem(
                route_id=int(route_id),
                boardings_avg=avg,
                load_pct=pct,
                tier=compute_load_tier(pct),
                sample_size=int(sample_size or 0),
            )
        )

    return RouteLoadListResponse(
        loads=items,
        count=len(items),
        source="predictions",
        from_date=resolved_from,
        to_date=resolved_to,
    )


async def _resolve_actuals_window(
    session: AsyncSession,
    from_date: datetime | None,
    to_date: datetime | None,
    default_days: int = 7,
) -> tuple[datetime, datetime, bool]:
    if from_date is not None and to_date is not None and from_date < to_date:
        return from_date, to_date, False

    max_stmt = select(func.max(Actual.period_start))
    max_ts = (await session.execute(max_stmt)).scalar()
    if max_ts is None:
        empty = datetime(1970, 1, 1, tzinfo=UTC)
        return empty, empty + timedelta(days=default_days), True
    if max_ts.tzinfo is None:
        max_ts = max_ts.replace(tzinfo=UTC)
    resolved_to = max_ts
    resolved_from = max_ts - timedelta(days=default_days)
    if from_date is not None:
        resolved_from = from_date
        if to_date is not None:
            resolved_to = to_date
    elif to_date is not None:
        resolved_to = to_date
        resolved_from = to_date - timedelta(days=default_days)
    return resolved_from, resolved_to, True


@router.get(
    "/historical/load",
    response_model=RouteLoadListResponse,
    summary="T-218: Summary actuals — avg load per route (block 'kak bylo', fallback MAX period)",
)
async def get_historical_load(
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    tram_capacity: int = Query(default=DEFAULT_TRAM_CAPACITY, ge=50, le=500),
    session: AsyncSession = Depends(get_db),
) -> RouteLoadListResponse:
    """Srednie boardings + load_pct za marshrutami (actuals).

    Yesli from/to ne zadany → fallback na MAX(period_start) - 7d .. MAX.
    """
    resolved_from, resolved_to, used_fallback = await _resolve_actuals_window(
        session, from_date, to_date
    )

    stmt = (
        select(
            Actual.route_id,
            func.avg(Actual.value).label("boardings_avg"),
            func.count(Actual.id).label("sample_size"),
            func.max(Actual.period_end).label("period_end_max"),
            func.min(Actual.period_start).label("period_start_min"),
        )
        .where(
            Actual.period_start >= resolved_from,
            Actual.period_start <= resolved_to,
        )
        .group_by(Actual.route_id)
        .order_by(Actual.route_id)
    )
    rows = (await session.execute(stmt)).all()

    items: list[RouteLoadItem] = []
    for route_id, boardings_avg, sample_size, period_end_max, period_start_min in rows:
        avg = float(boardings_avg or 0.0)
        pct = compute_load_pct(avg, tram_capacity)
        items.append(
            RouteLoadItem(
                route_id=int(route_id),
                boardings_avg=avg,
                load_pct=pct,
                tier=compute_load_tier(pct),
                period_start=period_start_min,
                period_end=period_end_max,
                sample_size=int(sample_size or 0),
            )
        )

    return RouteLoadListResponse(
        loads=items,
        count=len(items),
        source="actuals",
        from_date=resolved_from,
        to_date=resolved_to,
        used_fallback=used_fallback,
    )
