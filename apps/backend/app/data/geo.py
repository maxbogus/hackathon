"""T-227: гео-каталог маршрутов (остановки + координаты) для карты Москвы.

Источник: `data/external/stops_routes.json` — пользовательская разметка
10 трамвайных маршрутов хакатона (142 остановки, см. T-168).

Почему на backend, а не на фронте (clinerule 02 / 08): фронт не читает `data/`
напрямую — контракт идёт через OpenAPI → Orval. Отсутствие/битый каталог —
не ошибка: карта просто остаётся без линий (demo-режим), endpoint отвечает
пустым списком вместо 500.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.schemas.geo import GeoRoute, GeoStop

# Путь относительно `settings.data_dir` (в Docker = /app/data, локально = <repo>/data).
GEO_CATALOG_RELATIVE = Path("external") / "stops_routes.json"


def catalog_path() -> Path:
    """Актуальный путь к каталогу (переопределяется через settings.data_dir)."""
    return settings.data_dir / GEO_CATALOG_RELATIVE


def _as_float(value: object) -> float | None:
    """float для int/float, None для всего прочего (bool — не число)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _parse_stops(raw: object) -> list[GeoStop]:
    """Строки каталога → GeoStop с order по порядку следования.

    Битые строки (нет name/lat/lon, не тот тип) молча пропускаются —
    каталог размечен вручную, устойчивость важнее строгости.
    """
    if not isinstance(raw, list):
        return []

    stops: list[GeoStop] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        lat = _as_float(row.get("lat"))
        lon = _as_float(row.get("lon"))
        if not isinstance(name, str) or not name:
            continue
        if lat is None or lon is None:
            continue
        stops.append(GeoStop(name=name, lat=lat, lon=lon, order=len(stops)))
    return stops


@lru_cache(maxsize=4)
def load_route_geo(path: Path) -> tuple[GeoRoute, ...]:
    """Прочитать каталог → кортеж GeoRoute, отсортированный по route_id.

    Кэшируется по пути (каталог меняется редко, файл ~12 КБ).
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(payload, dict):
        return ()

    routes: list[GeoRoute] = []
    for key, raw in payload.items():
        # Ключи `_comment` и прочие не-числовые пропускаем.
        if not isinstance(key, str) or not key.isdigit():
            continue
        stops = _parse_stops(raw)
        if not stops:
            continue
        routes.append(GeoRoute(route_id=int(key), stops=stops, n_stops=len(stops)))

    return tuple(sorted(routes, key=lambda route: route.route_id))


def get_route_geo() -> tuple[GeoRoute, ...]:
    """Каталог по текущему `settings.data_dir` (кэш — по конкретному пути)."""
    return load_route_geo(catalog_path())


__all__ = ["GEO_CATALOG_RELATIVE", "catalog_path", "get_route_geo", "load_route_geo"]
