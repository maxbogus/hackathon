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
from app.models import Prediction
from app.predictions_active import active_params, feature_state
from app.schemas.predictions_db import (
    PredictionPointDB,
    PredictionsDBResponse,
)

router = APIRouter(prefix="/api/v1", tags=["predictions-db"])


async def _resolve_filters(
    session: AsyncSession,
    *,
    model_id: str | None,
    feature_set: str | None,
    zeros_applied: bool | None,
    prefer_active: bool = False,
    active_model_id: str | None = None,
    active_feature_set: str | None = None,
    active_zeros: bool | None = None,
) -> tuple[str | None, str | None, bool | None]:
    """Дефолты чтения (T-230): активный набор → тогглы.

    Если `prefer_active` — параметры берутся ТОЛЬКО из активного набора
    (для фолбэка фронта, когда запрос по слайдерам вернул 0 точек).
    """
    if active_model_id is None and active_feature_set is None and active_zeros is None:
        active = await active_params(session)
        if active is not None:
            active_model_id = active.model_id
            active_feature_set = active.feature_set
            active_zeros = active.zeros_applied

    if prefer_active and active_feature_set is not None:
        return active_model_id, active_feature_set, active_zeros

    if feature_set is None:
        feature_set = active_feature_set or await _default_feature_set(session)
    if zeros_applied is None:
        zeros_applied = (
            active_zeros
            if active_zeros is not None
            else await _default_zeros_state(session)
        )
    if model_id is None:
        model_id = active_model_id
    return model_id, feature_set, zeros_applied


async def _default_zeros_state(session: AsyncSession) -> bool:
    """zeros_applied=True если хотя бы один zero_override enabled.

    Делегирует в `feature_state` (T-230: единый источник правды).
    """
    return (await feature_state(session)).zeros_applied


async def _default_feature_set(session: AsyncSession) -> str:
    """Дефолтный feature_set на основе enabled toggles (делегирует feature_state)."""
    return (await feature_state(session)).feature_set


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
    prefer_active: bool = Query(
        default=False,
        description=(
            "T-230: игнорировать coef/feature_set/zeros и взять параметры "
            "активного набора (фолбэк фронта, когда по слайдерам нет данных)."
        ),
    ),
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

    model_id, feature_set, zeros_applied = await _resolve_filters(
        session,
        model_id=model_id,
        feature_set=feature_set,
        zeros_applied=zeros_applied,
        prefer_active=prefer_active,
    )

    stmt = select(Prediction).where(
        Prediction.is_active.is_(True),  # T-230: только активный набор (без дублей)
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
    coef_weather: float = Query(default=1.0, ge=0, le=3),
    coef_event: float = Query(default=1.0, ge=0, le=3),
    coef_season: float = Query(default=1.0, ge=0, le=3),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Возвращает CSV (route;date;hour;prediction).

    Default params: zeros_applied=True, feature_set=with_all — соответствует
    best submission (F-083: 0.83455 platform score).

    Формат совместим с submission pipeline (clinerule 23):
      - separator `;`
      - колонки: route, date (YYYY-MM-DD), hour (0-23), prediction
      - header НЕ включён (для совместимости с ml platform scoring)

    Валидация (clinerule 23):
      - coef_weather/event/season ∈ [0, 3] (FastAPI Query ge/le → 422)
      - from_date < to_date (HTTPException 400)
    """
    if from_date >= to_date:
        raise HTTPException(status_code=400, detail="from_date must be < to_date")
    model_id, feature_set, zeros_applied = await _resolve_filters(
        session,
        model_id=model_id,
        feature_set=feature_set,
        zeros_applied=zeros_applied,
    )

    stmt = select(Prediction).where(
        Prediction.is_active.is_(True),  # T-230: только активный набор
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

    model_id, feature_set, zeros_applied = await _resolve_filters(
        session,
        model_id=model_id,
        feature_set=feature_set,
        zeros_applied=zeros_applied,
    )

    stmt = select(Prediction).where(
        Prediction.is_active.is_(True),  # T-230: только активный набор
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
