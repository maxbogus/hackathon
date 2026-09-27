"""Historical data API (T-195).

GET /api/v1/historical/{route_id}?from=YYYY-MM-DD&to=YYYY-MM-DD&granularity=day
  → возвращает historical boardings из таблицы actuals.

Если actuals пуста (нет данных за период) — возвращает пустой список.
Это нормально для dev-режима, где данные захардкожены.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Actual
from app.schemas.historical import ActualPoint, HistoricalResponse

# F-097: default window for /historical/{route_id} when client (e.g. PassengerMode
# routeLoad.ts) omits from/to. 7 days covers "latest hour" + week context.
DEFAULT_HISTORICAL_DAYS: int = 7

router = APIRouter(prefix="/api/v1", tags=["historical"])


def _resolve_history_window(
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[datetime, datetime]:
    """Return (from_date, to_date) for the historical query.

    F-097: Both are optional now. If neither is provided (or only one is),
    default to the last ``DEFAULT_HISTORICAL_DAYS`` days ending at
    ``datetime.now(UTC)``. If only ``from_date`` is provided, derive ``to_date``
    as ``from_date + DEFAULT_HISTORICAL_DAYS``. If only ``to_date`` is provided,
    derive ``from_date`` as ``to_date - DEFAULT_HISTORICAL_DAYS``.
    """
    now = datetime.now(UTC)
    if from_date is None and to_date is None:
        resolved_to: datetime = now
        resolved_from: datetime = now - timedelta(days=DEFAULT_HISTORICAL_DAYS)
    elif from_date is None:
        # mypy здесь всё ещё видит None в from_date, но условие сужает тип.
        assert to_date is not None
        resolved_from = to_date - timedelta(days=DEFAULT_HISTORICAL_DAYS)
        resolved_to = to_date
    else:
        resolved_from = from_date
        resolved_to = (
            from_date + timedelta(days=DEFAULT_HISTORICAL_DAYS)
            if to_date is None
            else to_date
        )
    return resolved_from, resolved_to


@router.get(
    "/historical/{route_id}",
    response_model=HistoricalResponse,
    summary="Historical boardings (actuals) for a route",
)
async def get_historical(
    route_id: int,
    from_date: datetime | None = Query(
        default=None,
        alias="from",
        description=(
            "Start date (inclusive). Optional — default = "
            f"to_date - {DEFAULT_HISTORICAL_DAYS} days (or now - "
            f"{DEFAULT_HISTORICAL_DAYS} days if both are omitted)."
        ),
    ),
    to_date: datetime | None = Query(
        default=None,
        alias="to",
        description=(
            "End date (inclusive). Optional — default = "
            f"from_date + {DEFAULT_HISTORICAL_DAYS} days (or now if both omitted)."
        ),
    ),
    granularity: str = Query(
        default="day",
        description="Aggregation granularity: hour | day",
        pattern="^(hour|day)$",
    ),
    session: AsyncSession = Depends(get_db),
) -> HistoricalResponse:
    """Возвращает исторические boardings из БД.

    Empty list — нормально, если actuals пуста (dev-режим).

    F-097: ``from`` и ``to`` стали опциональными. Если оба опущены — берётся
    последние ``DEFAULT_HISTORICAL_DAYS`` дней. Нужен для PassengerMode
    (routeLoad.ts), который агрегирует «последний час» без явного диапазона.
    """
    from_date, to_date = _resolve_history_window(from_date, to_date)
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
                period_end=(datetime.fromisoformat(d) + timedelta(days=1)).replace(
                    tzinfo=UTC
                ),
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
) -> dict[str, Any]:
    """Возвращает список route_id, для которых есть хотя бы 1 actual."""
    stmt = select(Actual.route_id).distinct().order_by(Actual.route_id)
    rows = (await session.execute(stmt)).scalars().all()
    return {"routes": list(rows), "count": len(rows)}
