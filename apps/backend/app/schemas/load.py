"""T-218: Схемы для /predictions/load и /historical/load (summary endpoints)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

LoadTierLiteral = Literal["green", "yellow", "red", "darkred"]


class RouteLoadItem(BaseModel):
    """Один маршрут — avg boardings + load_pct + tier."""

    route_id: int
    boardings_avg: float
    load_pct: float
    tier: LoadTierLiteral
    # period_start/end только для actuals (когда брали данные), None для predictions
    period_start: datetime | None = None
    period_end: datetime | None = None
    # sample_size — сколько точек усреднили (для доверия)
    sample_size: int = 0

    model_config = {"from_attributes": True}


class RouteLoadListResponse(BaseModel):
    """Ответ /predictions/load и /historical/load."""

    loads: list[RouteLoadItem]
    count: int
    # source = "predictions" или "actuals" — для фронта и логов
    source: str
    # какой реально диапазон использовался (после fallback)
    from_date: datetime | None = None
    to_date: datetime | None = None
    # использован ли fallback (MAX(period_start))
    used_fallback: bool = False
