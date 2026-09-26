"""Traffic features (T-124).

Источник: data/external/traffic_osm_moscow.json (hardcoded 40 точек).
Фичи для каждой остановки/mаршрута:
- traffic_n_intersections_500m: count перекрестков в радиусе 500m
- traffic_dist_main_road_km: расстояние до ближайшей точки каталога
- traffic_jam_level_avg_500m: средний jam_level в радиусе 500m

R3/R4 hackathon-rules: hardcoded JSON, offline, reproducible.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

__all__ = [
    "TRAFFIC_FEATURE_NAMES",
    "_haversine_km",
    "get_traffic_features",
    "load_traffic_catalog",
]

# Расположение JSON-каталога
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_PATH = _REPO_ROOT / "data" / "external" / "traffic_osm_moscow.json"

# Порядок имён фичей (для FEATURE_NAMES в xgboost_route)
TRAFFIC_FEATURE_NAMES: tuple[str, ...] = (
    "traffic_n_intersections_500m",
    "traffic_dist_main_road_km",
    "traffic_jam_level_avg_500m",
)


# Haversine


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками в км (формула Haversine)."""
    R = 6371.0  # Радиус Земли в км
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# JSON loader


def load_traffic_catalog() -> list[dict[str, Any]]:
    """Загрузить каталог traffic точек из data/external/traffic_osm_moscow.json.

    Returns:
        list[dict]: каждая точка имеет поля id, lat, lon, category, jam_level, notes.

    Raises:
        FileNotFoundError: если JSON не найден.
    """
    if not _CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Traffic catalog not found: {_CATALOG_PATH}. "
            f"Expected: 40 traffic points (intersections + tram_car_shared)."
        )
    raw = json.loads(_CATALOG_PATH.read_text())
    points = raw.get("_points", [])

    required = {"id", "lat", "lon", "category", "jam_level", "notes"}
    for p in points:
        missing = required - set(p.keys())
        if missing:
            raise ValueError(f"Point {p.get('id', '?')!r} missing fields: {missing}")
    return points


# Feature computation


def get_traffic_features(
    lat: float,
    lon: float,
    radius_km: float = 0.5,
) -> dict[str, float]:
    """Вычислить traffic-фичи для одной точки (lat, lon).

    Args:
        lat: широта (например 55.7558 для Кремля).
        lon: долгота.
        radius_km: радиус для подсчета перекрестков (default 0.5km).

    Returns:
        dict с 3 ключами (TRAFFIC_FEATURE_NAMES):
        - traffic_n_intersections_500m: int count перекрестков в radius_km
        - traffic_dist_main_road_km: расстояние до ближайшей точки каталога
        - traffic_jam_level_avg_500m: средний jam_level в радиусе radius_km
    """
    catalog = load_traffic_catalog()

    # Считаем расстояния и фильтруем по радиусу
    distances = []
    for point in catalog:
        d = _haversine_km(lat, lon, point["lat"], point["lon"])
        distances.append((d, point))

    # Все distances (для dist_main_road)
    if distances:
        dist_main_road = min(d[0] for d in distances)
    else:
        dist_main_road = float("inf")

    # Только в радиусе (для n_intersections и jam_level_avg)
    within_radius = [(d, p) for d, p in distances if d <= radius_km]
    n_intersections = len(within_radius)
    if n_intersections > 0:
        jam_level_avg = sum(p["jam_level"] for _, p in within_radius) / n_intersections
    else:
        jam_level_avg = 0.0

    return {
        "traffic_n_intersections_500m": float(n_intersections),
        "traffic_dist_main_road_km": float(dist_main_road),
        "traffic_jam_level_avg_500m": float(jam_level_avg),
    }
