"""Predictions from DB API (T-195).

GET  /api/v1/predictions/db/{route_id}      — список прогнозов из БД с фильтрами
GET  /api/v1/predictions/export.csv         — CSV download (default params = best)

Параметры фильтрации (default = state из feature_toggles/zero_overrides):
  - model_id: id модели (xgboost_v_default, xgboost_v_poi, ...)
  - feature_set: baseline | with_poi | with_traffic | ...
  - zeros_applied: bool (default из zero_overrides — лучший = ON)
  - coef_weather/event/season: float
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import FeatureToggle, Prediction, ZeroOverride
from app.schemas.predictions_db import (
    PredictionPointDB,
    PredictionsDBResponse,
)

router = APIRouter(prefix="/api/v1", tags=["predictions-db"])


async def _default_zeros_state(session: AsyncSession) -> bool:
    """zeros_applied=True если хотя бы один zero_override enabled."""
    stmt = select(ZeroOverride).where(ZeroOverride.enabled == True)
    rows = (await session.execute(stmt)).scalars().all()
    return len(rows) > 0


async def _default_feature_set(session: AsyncSession) -> str:
    """Дефолтный feature_set на основе enabled toggles."""
    stmt = select(FeatureToggle).where(FeatureToggle.enabled == True)
    rows = (await session.execute(stmt)).scalars().all()
    names = {r.name for r in rows}
    if {"use_poi", "use_weather", "use_events"}.issubset(names):
        return "with_all"
    if "use_poi" in names:
        return "with_poi"
    return "baseline"


@router.get(
    "/predictions/db/{route_id}",
    response_model=PredictionsDBResponse,
    summary="Predictions for route (from DB with feature_set / zeros filters)",
)
async def get_predictions_db(
    route_id: int,
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
    model_id: str | None = Query(default=None),
    feature_set: str | None = Query(default=None),
    zeros_applied: bool | None = Query(default=None),
    horizon: Literal["day", "month", "year"] = Query(default="day"),
    granularity: Literal["hour", "day", "month"] = Query(default="hour"),
    coef_weather: float = Query(default=1.0, ge=0, le=3),
    coef_event: float = Query(default=1.0, ge=0, le=3),
    coef_season: float = Query(default=1.0, ge=0, le=3),
    session: AsyncSession = Depends(get_db),
) -> PredictionsDBResponse:
    """Возвращает прогнозы из БД с фильтрацией.

    Если filters=None — использует дефолты из feature_toggles + zero_overrides.
    """
    if from_date >= to_date:
        raise HTTPException(status_code=400, detail="from_date must be < to_date")

    if feature_set is None:
        feature_set = await _default_feature_set(session)
    if zeros_applied is None:
        zeros_applied = await _default_zeros_state(session)

    stmt = select(Prediction).where(
        Prediction.route_id == route_id,
        Prediction.horizon == horizon,
        Prediction.granularity == granularity,
        Prediction.period_start >= from_date,
        Prediction.period_start <= to_date,
        Prediction.coef_weather == coef_weather,
        Prediction.coef_event == coef_event,
        Prediction.coef_season == coef_season,
    )
    if model_id is not None:
        stmt = stmt.where(Prediction.model_id == model_id)
    if feature_set is not None:
        stmt = stmt.where(Prediction.feature_set == feature_set)
    if zeros_applied is not None:
        stmt = stmt.where(Prediction.zeros_applied == zeros_applied)

    stmt = stmt.order_by(Prediction.period_start)
    rows = (await session.execute(stmt)).scalars().all()

    points = [
        PredictionPointDB(
            period_start=r.period_start,
            period_end=r.period_end,
            value=r.value,
            lower=r.lower,
            upper=r.upper,
            horizon=r.horizon,
            granularity=r.granularity,
            feature_set=r.feature_set,
            zeros_applied=r.zeros_applied,
            coef_weather=r.coef_weather,
            coef_event=r.coef_event,
            coef_season=r.coef_season,
        )
        for r in rows
    ]
    return PredictionsDBResponse(
        route_id=route_id,
        from_date=from_date,
        to_date=to_date,
        model_id=model_id,
        feature_set=feature_set,
        zeros_applied=zeros_applied,
        points=points,
    )


@router.get(
    "/predictions/export.csv",
    summary="Export predictions as CSV (default params = best submission)",
)
async def export_predictions_csv(
    from_date: datetime = Query(default=datetime(2025, 11, 1, tzinfo=UTC)),
    to_date: datetime = Query(default=datetime(2025, 12, 31, 23, tzinfo=UTC)),
    model_id: str | None = Query(default=None),
    feature_set: str | None = Query(default=None),
    zeros_applied: bool | None = Query(default=None),
    coef_weather: float = Query(default=1.0),
    coef_event: float = Query(default=1.0),
    coef_season: float = Query(default=1.0),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Возвращает CSV (route;date;hour;prediction).

    Default params: zeros_applied=True, feature_set=with_all — соответствует
    best submission (F-083: 0.83455 platform score).

    Формат совместим с submission pipeline (clinerule 23):
      - separator `;`
      - колонки: route, date (YYYY-MM-DD), hour (0-23), prediction
      - header НЕ включён (для совместимости с ml platform scoring)
    """
    if feature_set is None:
        feature_set = await _default_feature_set(session)
    if zeros_applied is None:
        zeros_applied = await _default_zeros_state(session)

    stmt = select(Prediction).where(
        Prediction.period_start >= from_date,
        Prediction.period_start <= to_date,
        Prediction.coef_weather == coef_weather,
        Prediction.coef_event == coef_event,
        Prediction.coef_season == coef_season,
    )
    if model_id is not None:
        stmt = stmt.where(Prediction.model_id == model_id)
    stmt = stmt.where(Prediction.feature_set == feature_set)
    stmt = stmt.where(Prediction.zeros_applied == zeros_applied)
    stmt = stmt.order_by(Prediction.route_id, Prediction.period_start)

    rows = (await session.execute(stmt)).scalars().all()

    lines = []
    for r in rows:
        date_str = r.period_start.date().isoformat()
        hour = r.period_start.hour
        lines.append(f"{r.route_id};{date_str};{hour};{r.value:.2f}")
    csv = "\n".join(lines) + ("\n" if lines else "")

    md5 = hashlib.md5(csv.encode("utf-8")).hexdigest()

    fs_label = (model_id or feature_set or "default").replace("/", "_")
    filename = (
        f"submission_{fs_label}_{from_date.strftime('%Y%m%d')}"
        f"_{to_date.strftime('%Y%m%d')}.csv"
    )
    return Response(
        content=csv,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Row-Count": str(len(rows)),
            "X-CSV-MD5": md5,
        },
    )


@router.get(
    "/predictions/export.xlsx",
    summary="Export predictions as XLSX (T-206: альтернатива CSV для аналитиков)",
)
async def export_predictions_xlsx(
    from_date: datetime = Query(
        default=datetime(2025, 11, 1, tzinfo=UTC), alias="from"
    ),
    to_date: datetime = Query(
        default=datetime(2025, 12, 31, 23, tzinfo=UTC), alias="to"
    ),
    model_id: str | None = Query(default=None),
    feature_set: str | None = Query(default=None),
    zeros_applied: bool | None = Query(default=None),
    coef_weather: float = Query(default=1.0),
    coef_event: float = Query(default=1.0),
    coef_season: float = Query(default=1.0),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Возвращает XLSX (route, date, hour, prediction + coef колонки).

    Удобно для аналитиков, которые работают в Excel/LibreOffice.
    Default params = best submission (F-083, 0.83455).
    """
    import io

    from openpyxl import Workbook

    if feature_set is None:
        feature_set = await _default_feature_set(session)
    if zeros_applied is None:
        zeros_applied = await _default_zeros_state(session)

    stmt = select(Prediction).where(
        Prediction.period_start >= from_date,
        Prediction.period_start <= to_date,
        Prediction.coef_weather == coef_weather,
        Prediction.coef_event == coef_event,
        Prediction.coef_season == coef_season,
    )
    if model_id is not None:
        stmt = stmt.where(Prediction.model_id == model_id)
    stmt = stmt.where(Prediction.feature_set == feature_set)
    stmt = stmt.where(Prediction.zeros_applied == zeros_applied)
    stmt = stmt.order_by(Prediction.route_id, Prediction.period_start)

    rows = (await session.execute(stmt)).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "predictions"
    # Header
    ws.append(
        [
            "route",
            "date",
            "hour",
            "prediction",
            "model_id",
            "feature_set",
            "zeros_applied",
            "coef_weather",
            "coef_event",
            "coef_season",
        ]
    )
    for r in rows:
        ws.append(
            [
                r.route_id,
                r.period_start.date().isoformat(),
                r.period_start.hour,
                float(r.value),
                r.model_id,
                r.feature_set,
                bool(r.zeros_applied),
                float(r.coef_weather),
                float(r.coef_event),
                float(r.coef_season),
            ]
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    content = buf.read()

    fs_label = (model_id or feature_set or "default").replace("/", "_")
    filename = (
        f"submission_{fs_label}_{from_date.strftime('%Y%m%d')}"
        f"_{to_date.strftime('%Y%m%d')}.xlsx"
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Row-Count": str(len(rows)),
        },
    )
