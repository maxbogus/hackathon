"""Tests for spravochnik_geo.py (T-156: route geo-features).

Использует реальные справочники из data/real/spravochniki/.
RED-тесты пишутся ДО реализации (clinerule 16).
"""
from __future__ import annotations

from transit_ai.data.spravochnik_geo import (
    build_route_geo_features,
    load_user_routes,
)


def test_load_user_routes_returns_5_missing_routes() -> None:
    """T-156: user-provided routes (17/25/26/28/50) загружаются."""
    user_routes = load_user_routes()
    assert set(user_routes.keys()) == {17, 25, 26, 28, 50}
    assert user_routes[17]["n_stops"] == 52
    assert user_routes[50]["n_stops"] == 82


def test_build_route_geo_features_returns_all_10_routes() -> None:
    """T-156: все 10 маршрутов получают geo-фичи."""
    geo = build_route_geo_features()
    assert geo.shape[0] == 10
    assert set(geo["route"].tolist()) == {1, 5, 7, 11, 12, 17, 25, 26, 28, 50}


def test_build_route_geo_features_has_required_columns() -> None:
    """T-156: обязательные колонки в результате."""
    geo = build_route_geo_features()
    required = {
        "route", "n_stops", "lat_mid", "lon_mid", "lat_first", "lon_first",
        "lat_last", "lon_last", "dist_center_km", "primary_place_id",
    }
    assert required.issubset(geo.columns), f"missing: {required - set(geo.columns)}"


def test_routes_in_spravochnik_have_real_coords() -> None:
    """T-156: 5 маршрутов из справочника (1,5,7,11,12) имеют реальные координаты."""
    geo = build_route_geo_features()
    for r in (1, 5, 7, 11, 12):
        row = geo[geo.route == r].iloc[0]
        assert row["n_stops"] > 0, f"route {r} n_stops=0"
        assert 55.5 < row["lat_mid"] < 55.9
        assert 37.3 < row["lon_mid"] < 37.9


def test_routes_not_in_spravochnik_have_user_coords() -> None:
    """T-156: 5 маршрутов вне справочника получают координаты от user."""
    geo = build_route_geo_features()
    for r in (17, 25, 26, 28, 50):
        row = geo[geo.route == r].iloc[0]
        assert row["n_stops"] > 0, f"route {r} n_stops=0"
        assert 55.5 < row["lat_mid"] < 55.9
        assert 37.3 < row["lon_mid"] < 37.9


def test_dist_center_is_reasonable_for_all_routes() -> None:
    """T-156: dist_center_km в диапазоне 0..30 км."""
    geo = build_route_geo_features()
    for _, row in geo.iterrows():
        assert 0 < row["dist_center_km"] < 30, (
            f"route {row['route']} dist_center={row['dist_center_km']:.2f} unrealistic"
        )


def test_primary_place_id_is_known_depot() -> None:
    """T-156: primary_place_id ∈ known depots."""
    geo = build_route_geo_features()
    known = {39706, 39707, 39708, 39709, 39710, 39711}
    for _, row in geo.iterrows():
        assert int(row["primary_place_id"]) in known, (
            f"route {row['route']} primary_place_id={row['primary_place_id']}"
        )
