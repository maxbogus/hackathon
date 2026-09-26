"""Historical data API (T-195).

GET /api/v1/historical/{route_id}?from=YYYY-MM-DD&to=YYYY-MM-DD&granularity=day
  → возвращает historical boardings из таблицы actuals.

Если actuals пуста (нет данных за период) — возвращает пустой список.
Это нормально для dev-режима, где данные захардкожены.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Actual
from app.schemas.historical import ActualPoint, HistoricalResponse

router = APIRouter(prefix="/api/v1", tags=["historical"])


@router.get(
    "/historical/{route_id}",
    response_model=HistoricalResponse,
    summary="Historical boardings (actuals) for a route",
)
async def get_historical(
    route_id: int,
    from_date: datetime = Query(..., alias="from", description="Start date (inclusive)"),
    to_date: datetime = Query(..., alias="to", description="End date (inclusive)"),
    granularity: str = Query(
        default="day",
        description="Aggregation granularity: hour | day",
        pattern="^(hour|day)$",
    ),
    session: AsyncSession = Depends(get_db),
) -> HistoricalResponse:
    """Возвращает исторические boardings из БД.

    Empty list — нормально, если actuals пуста (dev-режим).
    """
    if from_date >= to_date:
        raise HTTPException(status_code=400, detail="from_date must be < to_date")

    if granularity == "day":
        # Агрегируем по дням
        stmt = (
            select(Actual)
            .where(
                Actual.route_id == route_id,
                Actual.period_start >= from_date,
                Actual.period_start <= to_date + timedelta(days=1),
            )
            .order_by(Actual.period_start)
        )
        rows = (await session.execute(stmt)).scalars().all()
        # Bucket by date
        buckets: dict[str, float] = {}
        for r in rows:
            key = r.period_start.date().isoformat()
            buckets[key] = buckets.get(key, 0.0) + r.value
        points = [
            ActualPoint(
                period_start=datetime.fromisoformat(d).replace(tzinfo=UTC),
                period_end=(datetime.fromisoformat(d) + timedelta(days=1)).replace(tzinfo=UTC),
                value=v,
            )
            for d, v in sorted(buckets.items())
        ]
    else:
        stmt = (
            select(Actual)
            .where(
                Actual.route_id == route_id,
                Actual.period_start >= from_date,
                Actual.period_start <= to_date,
            )
            .order_by(Actual.period_start)
        )
        rows = (await session.execute(stmt)).scalars().all()
        points = [
            ActualPoint(
                period_start=r.period_start,
                period_end=r.period_end,
                value=r.value,
            )
            for r in rows
        ]

    return HistoricalResponse(
        route_id=route_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        points=points,
    )


@router.get(
    "/historical",
    summary="List available routes with historical data",
)
async def list_routes_with_history(
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Возвращает список route_id, для которых есть хотя бы 1 actual."""
    stmt = select(Actual.route_id).distinct().order_by(Actual.route_id)
    rows = (await session.execute(stmt)).scalars().all()
    return {"routes": list(rows), "count": len(rows)}
