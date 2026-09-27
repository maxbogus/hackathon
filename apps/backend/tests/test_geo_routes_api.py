"""Tests for T-227: GET /api/v1/geo/routes + каталог `data/external/stops_routes.json`.

RED → GREEN → REFACTOR (clinerule 16).

Контракт (frontend `src/components/Map`):
    GET /api/v1/geo/routes →
        {"routes": [{"route_id": int, "n_stops": int,
                     "stops": [{"name": str, "lat": float, "lon": float, "order": int}]}],
         "count": int, "source": str}

Зачем: карта Москвы (T-122) рисует линии маршрутов и точки остановок. Геометрия
живёт в backend-каталоге (contract-first — фронт не читает `data/` напрямую,
clinerule 02/08). Остановки берутся из пользовательской разметки 10 маршрутов.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.data.geo import GEO_CATALOG_RELATIVE, get_route_geo, load_route_geo
from app.main import create_app

# Bbox Москвы (с запасом на окраины: Некрасовка/Бутово/Химки-граница).
MOSCOW_BBOX = {"lat_min": 55.4, "lat_max": 56.0, "lon_min": 37.2, "lon_max": 37.9}

HACKATHON_ROUTES = {1, 5, 7, 11, 12, 17, 25, 26, 28, 50}


@pytest.fixture
def client() -> TestClient:
    """Geo-эндпоинту БД не нужна — поднимаем приложение как есть."""
    return TestClient(create_app())


def _write_catalog(tmp_path: Path, payload: dict) -> Path:
    external = tmp_path / "external"
    external.mkdir(parents=True, exist_ok=True)
    catalog = external / "stops_routes.json"
    catalog.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return catalog


# --- unit: парсер каталога -------------------------------------------------


def test_load_route_geo_parses_stops_with_order(tmp_path: Path) -> None:
    catalog = _write_catalog(
        tmp_path,
        {
            "_comment": "test fixture",
            "7": [
                {"name": "A", "lat": 55.80, "lon": 37.70},
                {"name": "B", "lat": 55.79, "lon": 37.69},
            ],
            "1": [{"name": "C", "lat": 55.75, "lon": 37.60}],
        },
    )

    routes = load_route_geo(catalog)

    # Отсортировано по route_id (детерминизм контракта).
    assert [r.route_id for r in routes] == [1, 7]
    assert routes[1].n_stops == 2
    assert [s.order for s in routes[1].stops] == [0, 1]
    assert routes[1].stops[0].name == "A"
    assert routes[1].stops[0].lat == pytest.approx(55.80)
    assert routes[1].stops[0].lon == pytest.approx(37.70)


def test_load_route_geo_skips_comment_key_and_bad_rows(tmp_path: Path) -> None:
    catalog = _write_catalog(
        tmp_path,
        {
            "_comment": "ignored",
            "1": [
                {"name": "ok", "lat": 55.75, "lon": 37.60},
                {"name": "no coords"},
                {"lat": 55.75, "lon": 37.60},
            ],
        },
    )

    routes = load_route_geo(catalog)

    assert len(routes) == 1
    assert [s.name for s in routes[0].stops] == ["ok"]


def test_load_route_geo_missing_file_is_graceful(tmp_path: Path) -> None:
    """Отсутствие каталога — не 500, а пустой список (demo-режим без data/)."""
    assert load_route_geo(tmp_path / "external" / "nope.json") == ()


def test_load_route_geo_malformed_file_is_graceful(tmp_path: Path) -> None:
    bad = tmp_path / "external"
    bad.mkdir(parents=True, exist_ok=True)
    (bad / "stops_routes.json").write_text("{not json", encoding="utf-8")

    assert load_route_geo(bad / "stops_routes.json") == ()


# --- unit: реальный каталог репозитория -----------------------------------


def test_real_catalog_covers_hackathon_routes() -> None:
    routes = get_route_geo()

    assert {r.route_id for r in routes} == HACKATHON_ROUTES
    for route in routes:
        assert route.n_stops >= 5, f"route {route.route_id} has too few stops"
        assert route.n_stops == len(route.stops)


def test_real_catalog_coordinates_inside_moscow_bbox() -> None:
    for route in get_route_geo():
        for stop in route.stops:
            assert MOSCOW_BBOX["lat_min"] <= stop.lat <= MOSCOW_BBOX["lat_max"], (
                stop.name
            )
            assert MOSCOW_BBOX["lon_min"] <= stop.lon <= MOSCOW_BBOX["lon_max"], (
                stop.name
            )


# --- API ------------------------------------------------------------------


def test_geo_routes_endpoint_returns_catalog(client: TestClient) -> None:
    response = client.get("/api/v1/geo/routes")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["routes"]) == 10
    assert body["source"] == str(GEO_CATALOG_RELATIVE)

    first = body["routes"][0]
    assert first["route_id"] == 1
    assert first["n_stops"] == len(first["stops"]) >= 5
    assert first["stops"][0]["order"] == 0
    assert isinstance(first["stops"][0]["lat"], float)


def test_geo_routes_endpoint_is_graceful_without_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Если каталог не найден — 200 + пустой список (не 500)."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    load_route_geo.cache_clear()

    response = TestClient(create_app()).get("/api/v1/geo/routes")

    assert response.status_code == 200
    assert response.json() == {
        "routes": [],
        "count": 0,
        "source": str(GEO_CATALOG_RELATIVE),
    }
