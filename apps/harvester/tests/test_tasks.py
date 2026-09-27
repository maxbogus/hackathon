"""Тесты Celery-тасков harvester (T-193 → T-231: делегирование в app.build).

Таски в `local`-режиме нормализуют raw-файлы в `data/external/normalized/`
через `app.build.builders`; `fetch_all` пишет ещё и `manifest.json`.
Таски гоняем синхронно через `.apply()` (без брокера).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.tasks import (
    fetch_all,
    fetch_events_json,
    fetch_poi_json,
    fetch_traffic_json,
    fetch_weather_json,
)
import pytest

WEATHER_CSV = (
    "date,temp_max,temp_min,precipitation_sum,snowfall_sum,wind_speed_max\n"
    "2025-01-01,1.3,-6.8,3.9,2.66,19.8\n"
    "2025-01-02,3.1,1.3,2.0,0.07,26.8\n"
)

EXPECTED_SOURCES = {
    "weather",
    "traffic",
    "poi",
    "events",
    "stops",
    "validators",
    "calendar",
    "user_routes",
}


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Мини-репозиторий: data/external/* + ml/.../_user_routes_2025.json."""
    ext = tmp_path / "data" / "external"
    ext.mkdir(parents=True)
    (ext / "weather_2025.csv").write_text(WEATHER_CSV, encoding="utf-8")
    (ext / "traffic_osm_moscow.json").write_text(
        json.dumps(
            {
                "_points": [
                    {
                        "id": "t1",
                        "lat": 55.7,
                        "lon": 37.6,
                        "category": "major_arterial",
                        "jam_level": 3,
                        "notes": "n",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (ext / "poi_moscow.json").write_text(
        json.dumps([{"name": "МГУ", "category": "university", "lat": 55.7, "lon": 37.53}]),
        encoding="utf-8",
    )
    (ext / "events_moscow.json").write_text(
        json.dumps(
            {
                "_events": [
                    {
                        "id": "e1",
                        "date": "2025-11-04",
                        "category": "holiday",
                        "magnitude": 1.0,
                        "tau_days": 7,
                        "affected_routes": [],
                        "notes": "n",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (ext / "stops_routes.json").write_text(
        json.dumps({"_comment": "c", "1": [{"name": "A", "lat": 55.6, "lon": 37.5}]}),
        encoding="utf-8",
    )
    (ext / "validators_lookup.csv").write_text(
        "route_id,weekday,hour,n_validators_mean,n_trams_mean\n1,0,0,2.0,1.0\n",
        encoding="utf-8",
    )
    (ext / "holidays_ru_2025.json").write_text(
        json.dumps({"holidays": ["2025-11-04"]}), encoding="utf-8"
    )
    (ext / "school_breaks_2025.json").write_text(
        json.dumps({"school_breaks": [["2025-10-27", "2025-11-04"]]}), encoding="utf-8"
    )
    ml_data = tmp_path / "ml" / "transit_ai" / "data"
    ml_data.mkdir(parents=True)
    (ml_data / "_user_routes_2025.json").write_text(
        json.dumps({"_comment": "c", "17": {"n_stops": 52}}), encoding="utf-8"
    )

    monkeypatch.setattr("app.config.settings.data_dir", tmp_path / "data")
    monkeypatch.setattr("app.config.settings.external_dir", ext)
    monkeypatch.setattr("app.tasks.settings.data_dir", tmp_path / "data")
    monkeypatch.setattr("app.tasks.settings.external_dir", ext)
    return tmp_path


def _normalized(repo: Path, name: str) -> dict:
    path = repo / "data" / "external" / "normalized" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_fetch_weather_builds_normalized(fake_repo: Path) -> None:
    res = fetch_weather_json.apply().get()

    assert res["source"] == "weather"
    assert res["rows"] == 2
    payload = _normalized(fake_repo, "weather.json")
    assert payload["rows"][0]["date"] == "2025-01-01"
    assert payload["rows"][0]["temp_max"] == 1.3


def test_fetch_traffic_supports_points_schema(fake_repo: Path) -> None:
    """traffic_osm_moscow.json использует `_points`, а не Overpass `elements`."""
    res = fetch_traffic_json.apply().get()

    assert res["source"] == "traffic"
    assert res["rows"] == 1


def test_fetch_poi_builds_normalized(fake_repo: Path) -> None:
    res = fetch_poi_json.apply().get()

    assert res["source"] == "poi"
    assert res["rows"] == 1


def test_fetch_events_supports_underscore_events(fake_repo: Path) -> None:
    """events_moscow.json использует ключ `_events` (T-172)."""
    res = fetch_events_json.apply().get()

    assert res["source"] == "events"
    assert res["rows"] == 1


def test_fetch_all_writes_manifest(fake_repo: Path) -> None:
    res = fetch_all.apply().get()

    assert res["status"] == "ok"
    assert set(res["results"]) >= EXPECTED_SOURCES
    manifest = _normalized(fake_repo, "manifest.json")
    assert set(manifest["sources"]) >= EXPECTED_SOURCES
    for meta in manifest["sources"].values():
        assert len(meta["output_sha256"]) == 64


def test_local_mode_makes_no_http_calls(fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4: в local-режиме таски не ходят в сеть."""

    class _Boom:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("local mode must not create http clients")

    monkeypatch.setattr("app.tasks.httpx.Client", _Boom)

    assert fetch_all.apply().get()["status"] == "ok"
