"""T-227: схемы гео-каталога маршрутов (остановки + координаты) для карты.

Контракт для GET /api/v1/geo/routes. Фронт (T-122, `src/components/Map`)
рисует по этим данным линии маршрутов и точки остановок, окрашивая их
тем же tier'ом, что и карточки на дашборде (`/api/v1/predictions/load`).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeoStop(BaseModel):
    """Одна остановка маршрута с координатами."""

    name: str
    lat: float
    lon: float
    # Порядок следования по маршруту (0-based) — фронт соединяет линией по нему.
    order: int = Field(ge=0)


class GeoRoute(BaseModel):
    """Маршрут = упорядоченный список остановок."""

    route_id: int
    stops: list[GeoStop]
    n_stops: int


class GeoRoutesResponse(BaseModel):
    """Ответ GET /api/v1/geo/routes."""

    routes: list[GeoRoute]
    count: int
    # Что за источник (для логов/фронта): относительный путь каталога.
    source: str
