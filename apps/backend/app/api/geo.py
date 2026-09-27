"""Geo API (T-227).

GET /api/v1/geo/routes — остановки 10 маршрутов с координатами, для карты (T-122).

Почему отдельный роутер, а не в /predictions/load: геометрия маршрута —
статичный справочник, а не прогноз. Фронт мёржит её с tier'ом из
`/predictions/load` (один контракт — одна ответственность).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.data.geo import GEO_CATALOG_RELATIVE, get_route_geo
from app.schemas.geo import GeoRoutesResponse

router = APIRouter(prefix="/api/v1", tags=["geo"])


@router.get(
    "/geo/routes",
    response_model=GeoRoutesResponse,
    summary="T-227: Справочник остановок маршрутов (для карты)",
)
async def get_geo_routes() -> GeoRoutesResponse:
    """Остановки всех маршрутов хакатона с координатами.

    Пустой `routes` — не ошибка: каталог `data/external/stops_routes.json`
    может отсутствовать в demo-режиме (карта рендерит заглушку).
    """
    routes = list(get_route_geo())
    return GeoRoutesResponse(
        routes=routes,
        count=len(routes),
        source=str(GEO_CATALOG_RELATIVE),
    )
