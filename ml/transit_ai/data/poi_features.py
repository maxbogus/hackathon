"""POI (points-of-interest) features для трамвайных маршрутов (T-168).

Per-stop расчёт POI в радиусе от координат остановки маршрута.

Источники данных:
1. data/external/poi_moscow.json — 146 POI в 13 категориях.
2. data/external/stops_routes.json — 142 остановки 10 маршрутов с координатами.

API:
- count_poi_for_stop(lat, lon, category) — count одной категории
- dist_to_nearest(lat, lon, category) — расстояние в км
- get_stop_poi_features(lat, lon) — 15 фичей для точки
- get_route_poi_features(route_id) — per-stop для маршрута
- build_all_route_poi_features() — 142×15 для всех маршрутов

R4 hackathon-rules: no internet at runtime.
R3 reproducible: JSON-каталоги в data/external/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from transit_ai.data.spravochnik_geo import _haversine_km

# Конфигурация категорий
CATEGORY_RADIUS_KM: dict[str, float] = {
    "school": 0.5,
    "university": 1.5,
    "stadium": 1.5,
    "park": 1.0,
    "mall": 1.0,
    "theater": 1.0,
    "culture": 1.0,
    "market": 1.0,
    "clinic": 0.5,
    "hospital": 1.5,
    "cinema": 1.0,
    "train_station": 1.0,
    "metro_hub": 1.0,
}

CATEGORY_PLURAL: dict[str, str] = {
    "school": "schools",
    "university": "universities",
    "stadium": "stadiums",
    "park": "parks",
    "mall": "malls",
    "theater": "theaters",
    "culture": "culture",
    "market": "markets",
    "clinic": "clinics",
    "hospital": "hospitals",
    "cinema": "cinemas",
    "train_station": "train_stations",
    "metro_hub": "metro_hubs",
}

CATEGORY_WEIGHTS: dict[str, float] = {
    "school": 1.0,
    "university": 2.0,
    "stadium": 2.0,
    "park": 0.5,
    "mall": 1.5,
    "theater": 1.0,
    "culture": 0.8,
    "market": 1.0,
    "clinic": 1.5,
    "hospital": 1.5,
    "cinema": 0.8,
    "train_station": 2.5,
    "metro_hub": 2.0,
}

VALID_CATEGORIES: frozenset[str] = frozenset(CATEGORY_RADIUS_KM.keys())


def _column_name(category: str, radius_km: float) -> str:
    """n_<plural>_<radius><m|km>.

    Examples:
        school @ 0.5km → n_schools_500m
        university @ 1.5km → n_universities_1500m
        park @ 1.0km → n_parks_1km
    """
    plural = CATEGORY_PLURAL[category]
    if radius_km == int(radius_km):
        return f"n_{plural}_{int(radius_km)}km"
    return f"n_{plural}_{int(radius_km * 1000)}m"


# 13 категорий + 2 derived = 15 фичей
POI_FEATURE_NAMES: tuple[str, ...] = (
    _column_name("school", 0.5),
    _column_name("university", 1.5),
    _column_name("stadium", 1.5),
    _column_name("park", 1.0),
    _column_name("mall", 1.0),
    _column_name("theater", 1.0),
    _column_name("culture", 1.0),
    _column_name("market", 1.0),
    _column_name("clinic", 0.5),
    _column_name("hospital", 1.5),
    _column_name("cinema", 1.0),
    _column_name("train_station", 1.0),
    _column_name("metro_hub", 1.0),
    "dist_to_nearest_metro_km",
    "poi_score",
)


def _repo_root() -> Path:
    """hackathon/ — корень репо."""
    return Path(__file__).resolve().parents[3]


def load_poi_catalog() -> list[dict[str, Any]]:
    """Загрузить POI каталог из JSON."""
    path = _repo_root() / "data" / "external" / "poi_moscow.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_stops_catalog() -> dict[int, list[dict[str, Any]]]:
    """Загрузить каталог остановок маршрутов.

    Returns:
        dict[int, list[dict]]: ключ=route_id, значение=[{name, lat, lon}, ...].
    """
    path = _repo_root() / "data" / "external" / "stops_routes.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw.items() if k != "_comment"}


def count_poi_for_stop(
    lat: float, lon: float, category: str, radius_km: float | None = None
) -> int:
    """Подсчитать POI категории в радиусе от точки."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unknown category: {category}. Valid: {sorted(VALID_CATEGORIES)}")
    if radius_km is None:
        radius_km = CATEGORY_RADIUS_KM[category]
    catalog = load_poi_catalog()
    n = 0
    for p in catalog:
        if p["category"] != category:
            continue
        d_km = _haversine_km(lat, lon, float(p["lat"]), float(p["lon"]))
        if d_km <= radius_km:
            n += 1
    return n


def dist_to_nearest(lat: float, lon: float, category: str | None = None) -> float:
    """Расстояние до ближайшего POI (км). 99.0 если ничего не найдено."""
    catalog = load_poi_catalog()
    best = 99.0
    for p in catalog:
        if category is not None and p["category"] != category:
            continue
        d = _haversine_km(lat, lon, float(p["lat"]), float(p["lon"]))
        if d < best:
            best = d
    return best


def get_stop_poi_features(lat: float, lon: float) -> dict[str, float]:
    """15 POI-фичей для точки (lat, lon)."""
    feats: dict[str, float] = {}
    total_score = 0.0
    for cat in VALID_CATEGORIES:
        radius = CATEGORY_RADIUS_KM[cat]
        n = count_poi_for_stop(lat=lat, lon=lon, category=cat)
        feats[_column_name(cat, radius)] = float(n)
        total_score += n * CATEGORY_WEIGHTS[cat]
    feats["dist_to_nearest_metro_km"] = dist_to_nearest(lat=lat, lon=lon, category="metro_hub")
    feats["poi_score"] = total_score
    return feats


def get_route_poi_features(route_id: int) -> pd.DataFrame:
    """POI-фичи для всех остановок маршрута.

    Returns:
        pd.DataFrame: shape (n_stops, 15), index=stop_name.
    """
    stops = load_stops_catalog().get(route_id, [])
    rows = []
    for stop in stops:
        feats = get_stop_poi_features(lat=float(stop["lat"]), lon=float(stop["lon"]))
        feats["stop_name"] = stop["name"]
        rows.append(feats)
    if not rows:
        return pd.DataFrame(columns=list(POI_FEATURE_NAMES) + ["stop_name"]).set_index("stop_name")
    df = pd.DataFrame(rows).set_index("stop_name")
    return df[list(POI_FEATURE_NAMES)]


def build_all_route_poi_features() -> pd.DataFrame:
    """POI-фичи для всех 10 маршрутов.

    Returns:
        pd.DataFrame: shape (142, 17) — route_id + stop_name + 15 фичей.
    """
    frames = []
    for route_id, stops in load_stops_catalog().items():
        if not stops:
            continue
        df = get_route_poi_features(route_id)
        df["route_id"] = route_id
        frames.append(df.reset_index())
    if not frames:
        return pd.DataFrame(columns=list(POI_FEATURE_NAMES) + ["route_id", "stop_name"])
    out = pd.concat(frames, ignore_index=True)
    return out


# Legacy API (per-route) — сохранён для обратной совместимости.
def count_poi_in_radius(route_id: int, category: str, radius_km: float | None = None) -> int:
    """DEPRECATED: per-route count от ближайшей точки маршрута."""
    from transit_ai.data.spravochnik_geo import build_route_geo_features

    geo = build_route_geo_features()
    row_df = geo[geo["route"] == route_id]
    if row_df.empty:
        return 0
    row = row_df.iloc[0]
    points = []
    for col in ("lat_first", "lat_mid", "lat_last"):
        lat = row.get(col)
        lon = row.get(col.replace("lat_", "lon_"))
        if lat is not None and lon is not None:
            points.append((float(lat), float(lon)))
    if not points:
        return 0
    if radius_km is None:
        radius_km = CATEGORY_RADIUS_KM.get(category, 1.0)
    catalog = load_poi_catalog()
    n = 0
    for p in catalog:
        if p["category"] != category:
            continue
        min_d = min(
            _haversine_km(lat, lon, float(p["lat"]), float(p["lon"]))
            for (lat, lon) in points
        )
        if min_d <= radius_km:
            n += 1
    return n


def build_route_poi_features() -> pd.DataFrame:
    """DEPRECATED: per-route POI (для тестов T-168 v1)."""
    stops_cat = load_stops_catalog()
    rows = []
    for route_id in sorted(stops_cat.keys()):
        df = get_route_poi_features(route_id)
        if df.empty:
            continue
        row_agg = df.mean(numeric_only=True).to_dict()
        row_agg["route_id"] = route_id
        rows.append(row_agg)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).set_index("route_id")
    legacy_cols = [
        "n_schools_500m",
        "n_universities_3km",
        "n_stadiums_3km",
        "n_parks_1km",
        "n_malls_1km",
        "n_theaters_1km",
        "poi_density",
        "is_event_venue_route",
    ]
    for c in legacy_cols:
        if c not in out.columns:
            base = c.replace("_3km", "_1km").replace("_500m", "_500m")
            out[c] = out[base] if base in out.columns else 0
    if "poi_density" not in out.columns:
        count_cols = [c for c in out.columns if c.startswith("n_")]
        out["poi_density"] = out[count_cols].sum(axis=1)
    if "is_event_venue_route" not in out.columns:
        if "n_stadiums_1km" in out.columns and "n_theaters_1km" in out.columns:
            out["is_event_venue_route"] = (
                (out["n_stadiums_1km"] > 0) | (out["n_theaters_1km"] > 0)
            ).astype(int)
        else:
            out["is_event_venue_route"] = 0
    return out[legacy_cols]
