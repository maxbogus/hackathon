"""RED-тесты: geo-каталог читается из `normalized/stops.json` (шаг 0, T-231).

Backend получает остановки из нормализованного артефакта ETL, а не напрямую
из raw-разметки; raw-путь остаётся фолбэком (demo-режим без ETL).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import settings
from app.data.geo import catalog_path, get_route_geo, load_route_geo

NORMALIZED_ROUTES = {
    "7": [
        {"name": "A", "lat": 55.80, "lon": 37.70},
        {"name": "B", "lat": 55.79, "lon": 37.69},
    ],
    "1": [{"name": "C", "lat": 55.75, "lon": 37.60}],
}


def _write(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Изолированный data/ (пути резолвятся на каждом вызове catalog_path)."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    yield tmp_path


def test_catalog_path_prefers_normalized(data_dir: Path) -> None:
    raw = _write(
        data_dir / "external" / "stops_routes.json", {"1": NORMALIZED_ROUTES["1"]}
    )
    normalized = _write(
        data_dir / "external" / "normalized" / "stops.json",
        {"source": "stops", "routes": NORMALIZED_ROUTES},
    )

    assert catalog_path() == normalized

    normalized.unlink()
    assert catalog_path() == raw


def test_load_route_geo_reads_normalized_routes_key(data_dir: Path) -> None:
    normalized = _write(
        data_dir / "external" / "normalized" / "stops.json",
        {"source": "stops", "routes": NORMALIZED_ROUTES},
    )

    routes = load_route_geo(normalized)

    assert [r.route_id for r in routes] == [1, 7]
    assert routes[1].n_stops == 2
    assert routes[1].stops[0].name == "A"


def test_get_route_geo_uses_normalized_catalog(data_dir: Path) -> None:
    _write(
        data_dir / "external" / "normalized" / "stops.json",
        {"source": "stops", "routes": NORMALIZED_ROUTES},
    )

    routes = get_route_geo()

    assert {r.route_id for r in routes} == {1, 7}
