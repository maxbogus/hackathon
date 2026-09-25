"""Tests for traffic features (T-124).

Источник: data/external/traffic_osm_moscow.json (hardcoded, R3/R4 compliant).
Фичи: n_intersections_500m, dist_main_road_km, jam_level_avg_500m.

Использование:
    from transit_ai.data.traffic_osm import get_traffic_features
    feats = get_traffic_features(lat=55.7558, lon=37.6173)
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from transit_ai.data.traffic_osm import (
    TRAFFIC_FEATURE_NAMES,
    _haversine_km,
    get_traffic_features,
    load_traffic_catalog,
)


# Haversine

def test_haversine_zero_distance() -> None:
    assert _haversine_km(55.0, 37.0, 55.0, 37.0) == pytest.approx(0.0, abs=1e-9)


def test_haversine_known_distance_kremlin_to_msu() -> None:
    # Moscow Kremlin -> Moscow State University ~6-9km (зависит от маршрута)
    dist = _haversine_km(55.7520, 37.6175, 55.7038, 37.5306)
    assert 5.0 < dist < 10.0, f"Got {dist:.2f}km"


def test_haversine_short_distance_moscow_center() -> None:
    # Тверская -> Арбатская ~2km
    dist = _haversine_km(55.7615, 37.6105, 55.7525, 37.6015)
    assert 0.5 < dist < 3.0, f"Got {dist:.2f}km"


# JSON catalog

def test_load_traffic_catalog_returns_at_least_30() -> None:
    catalog = load_traffic_catalog()
    assert len(catalog) >= 30, f"Expected >=30 traffic points, got {len(catalog)}"


def test_load_traffic_catalog_required_fields() -> None:
    required = {"id", "lat", "lon", "category", "jam_level", "notes"}
    for point in load_traffic_catalog():
        missing = required - set(point.keys())
        assert not missing, f"Point {point.get('id', '?')!r} missing fields: {missing}"


def test_load_traffic_catalog_categories() -> None:
    catalog = load_traffic_catalog()
    categories = {p["category"] for p in catalog}
    assert "major_arterial" in categories
    assert "tram_car_shared" in categories


def test_load_traffic_catalog_moscow_bounds() -> None:
    for p in load_traffic_catalog():
        assert 55.5 <= p["lat"] <= 56.0, f"Out of bounds: {p['lat']}"
        assert 37.3 <= p["lon"] <= 37.9, f"Out of bounds: {p['lon']}"


def test_load_traffic_catalog_jam_level_range() -> None:
    """jam_level ∈ [0, 5] для каждой точки."""
    for p in load_traffic_catalog():
        assert 0.0 <= p["jam_level"] <= 5.0, f"Bad jam_level: {p['jam_level']}"


# Feature engineering

def test_traffic_feature_names_count() -> None:
    assert len(TRAFFIC_FEATURE_NAMES) == 3


def test_get_traffic_features_returns_all_keys() -> None:
    feats = get_traffic_features(lat=55.7558, lon=37.6173)
    assert set(feats.keys()) == set(TRAFFIC_FEATURE_NAMES)


def test_get_traffic_features_on_catalog_point_has_nonzero() -> None:
    """Если точка = одна из каталога, n_intersections >= 1 (вкл. её саму)."""
    # Kremlin есть в каталоге
    feats = get_traffic_features(lat=55.7520, lon=37.6175, radius_km=0.5)
    assert feats["traffic_n_intersections_500m"] >= 1


def test_get_traffic_features_far_from_catalog_zero_intersections() -> None:
    """Далеко от каталога - 0 перекрестков в 500m."""
    # Точка между Москвой и Зеленоградом (нет в каталоге)
    feats = get_traffic_features(lat=55.9500, lon=37.2000, radius_km=0.5)
    assert feats["traffic_n_intersections_500m"] == 0
    assert feats["traffic_jam_level_avg_500m"] == 0.0


def test_get_traffic_features_dist_main_road_always_present() -> None:
    """dist_main_road_km всегда есть (далеко от каталога = большое значение)."""
    feats = get_traffic_features(lat=55.9500, lon=37.2000)
    assert feats["traffic_dist_main_road_km"] > 5.0


def test_get_traffic_features_dist_main_road_smaller_in_center() -> None:
    """В центре dist_main_road меньше, чем за МКАД."""
    feats_center = get_traffic_features(lat=55.7558, lon=37.6173)
    feats_outskirts = get_traffic_features(lat=55.9500, lon=37.2000)
    assert feats_center["traffic_dist_main_road_km"] < feats_outskirts["traffic_dist_main_road_km"]


def test_get_traffic_features_jam_level_bounded() -> None:
    feats = get_traffic_features(lat=55.7558, lon=37.6173)
    assert 0.0 <= feats["traffic_jam_level_avg_500m"] <= 5.0


def test_get_traffic_features_no_negative_distances() -> None:
    feats = get_traffic_features(lat=55.7558, lon=37.6173)
    assert feats["traffic_dist_main_road_km"] >= 0.0
