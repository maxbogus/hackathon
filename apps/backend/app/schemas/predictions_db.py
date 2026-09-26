"""Schemas для /predictions endpoints (T-195).

Расширяет существующий /predictions/stop/{id} извлечением из БД
с фильтрацией по feature_set, model_id, zeros_applied.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PredictionPointDB(BaseModel):
    """Одна точка прогноза из БД."""

    period_start: datetime
    period_end: datetime
    value: float
    lower: float | None = None
    upper: float | None = None
    horizon: str
    granularity: str
    feature_set: str
    zeros_applied: bool
    coef_weather: float
    coef_event: float
    coef_season: float

    model_config = {"from_attributes": True}


class PredictionsDBResponse(BaseModel):
    """Ответ /predictions/db/{route_id}."""

    route_id: int
    from_date: datetime
    to_date: datetime
    model_id: str | None = None
    feature_set: str | None = None
    zeros_applied: bool | None = None
    points: list[PredictionPointDB]

    model_config = {"from_attributes": True}


class PredictionsExportResponse(BaseModel):
    """Ответ /predictions/export.csv."""

    csv: str = Field(..., description="CSV content (UTF-8)")
    filename: str = Field(..., description="Suggested filename")
    row_count: int
    md5: str
