"""Tests for harvester tasks.

We run tasks synchronously via `.apply()` to bypass the broker.
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


@pytest.fixture
def external_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake data/external/ with sample JSON files."""
    ext = tmp_path / "external"
    ext.mkdir()
    (ext / "weather_2025.csv").write_text(
        "date,temp_c,precip\n2025-01-01,-5.2,0.0\n2025-01-02,-3.1,1.2\n"
    )
    (ext / "traffic_osm_moscow.json").write_text(
        json.dumps({"elements": [{"id": 1}, {"id": 2}, {"id": 3}]})
    )
    (ext / "poi_moscow.json").write_text(
        json.dumps({"pois": [{"name": "Park", "category": "park"}]})
    )
    (ext / "events_moscow.json").write_text(
        json.dumps({"events": [{"date": "2025-11-04", "kind": "holiday"}]})
    )
    monkeypatch.setattr("app.tasks.settings.external_dir", ext)
    monkeypatch.setattr("app.config.settings.external_dir", ext)
    return ext


def test_fetch_weather_normalises_csv(external_dir: Path) -> None:
    res = fetch_weather_json.apply().get()
    assert res["source"] == "weather_openmeteo"
    assert res["rows"] == 2
    assert (external_dir / "weather_normalized.json").exists()
    payload = json.loads((external_dir / "weather_normalized.json").read_text())
    assert payload["rows"][0]["date"] == "2025-01-01"


def test_fetch_traffic_normalises_osm(external_dir: Path) -> None:
    res = fetch_traffic_json.apply().get()
    assert res["source"] == "traffic_osm"
    assert res["rows"] == 3


def test_fetch_poi_normalises(external_dir: Path) -> None:
    res = fetch_poi_json.apply().get()
    assert res["source"] == "poi_osm"
    assert res["rows"] == 1


def test_fetch_events_normalises(external_dir: Path) -> None:
    res = fetch_events_json.apply().get()
    assert res["source"] == "events_misc"
    assert res["rows"] == 1


def test_fetch_all_runs_all(external_dir: Path) -> None:
    res = fetch_all.apply().get()
    assert res["status"] == "ok"
    assert "weather" in res["results"]
    assert "traffic" in res["results"]
    assert "poi" in res["results"]
    assert "events" in res["results"]


def test_fetch_traffic_supports_points_schema(external_dir: Path) -> None:
    """T-124 traffic_osm_moscow.json uses `_points` instead of Overpass `elements`."""
    (external_dir / "traffic_osm_moscow.json").write_text(
        json.dumps({"_points": [{"lat": 55.7, "lon": 37.6, "jam": 3}]})
    )
    res = fetch_traffic_json.apply().get()
    assert res["rows"] == 1


def test_fetch_events_supports_underscore_events(external_dir: Path) -> None:
    """T-172 events_moscow.json uses `_events` key."""
    (external_dir / "events_moscow.json").write_text(
        json.dumps({"_events": [{"date": "2025-11-04", "kind": "holiday"}]})
    )
    res = fetch_events_json.apply().get()
    assert res["rows"] == 1
