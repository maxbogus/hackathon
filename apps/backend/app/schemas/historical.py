"""Schemas для /historical endpoints (T-195).

Возвращает historical boardings (actuals) агрегированные по маршруту и периоду.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ActualPoint(BaseModel):
    """Одна точка данных: route × datetime → value."""

    period_start: datetime
    period_end: datetime
    value: float = Field(..., description="Historical boardings count")


class HistoricalResponse(BaseModel):
    """Ответ /historical/{route_id}."""

    route_id: int
    from_date: datetime
    to_date: datetime
    granularity: str = Field(..., description="hour | day")
    points: list[ActualPoint]

    model_config = {"from_attributes": True}
