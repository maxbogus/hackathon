"""RED-тесты: ML-читатели предпочитают `normalized/*.json`, но умеют raw-фолбэк.

Шаг 0 (T-231): ETL в apps/harvester пишет `data/external/normalized/*.json`.
Эти тесты фиксируют контракт «normalized первым, raw вторым» и доказывают,
что результат не зависит от выбранного пути (метрики не поедут).

Запуск: cd ml && uv run pytest tests/test_external_normalized_preference.py -v --no-cov
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from transit_ai.data import (
    events_calendar,
    poi_features,
    traffic_osm,
    validators_lookup,
    weather_openmeteo,
)

WEATHER_ROWS = [
    {
        "date": "2025-01-01",
        "temp_max": 1.3,
        "temp_min": -6.8,
        "precipitation_sum": 3.9,
        "snowfall_sum": 2.66,
        "wind_speed_max": 19.8,
    }
]

TRAFFIC_POINTS = [
    {
        "id": "t1",
        "lat": 55.75,
        "lon": 37.61,
        "category": "major_arterial",
        "jam_level": 4,
        "notes": "n",
    }
]

POIS = [{"name": "МГУ", "category": "university", "lat": 55.7038, "lon": 37.5306}]
STOPS = {"1": [{"name": "Чертаново", "lat": 55.60112, "lon": 37.585266}]}
EVENTS = [
    {
        "id": "e1",
        "date": "2025-09-13",
        "category": "metro_open",
        "magnitude": 1.1,
        "tau_days": 60,
        "affected_routes": [],
        "notes": "n",
    }
]
VALIDATOR_ROWS = [
    {
        "route_id": 1,
        "weekday": 0,
        "hour": 0,
        "n_validators_mean": 2.0,
        "n_trams_mean": 1.0,
    }
]


def _write(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_weather_prefers_normalized_then_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv = tmp_path / "weather_2025.csv"
    csv.write_text(
        "date,temp_max,temp_min,precipitation_sum,snowfall_sum,wind_speed_max\n"
        "2025-01-01,1.3,-6.8,3.9,2.66,19.8\n",
        encoding="utf-8",
    )
    normalized = _write(
        tmp_path / "normalized" / "weather.json", {"rows": WEATHER_ROWS}
    )
    monkeypatch.setattr(weather_openmeteo, "_CACHE_PATH", csv)
    monkeypatch.setattr(weather_openmeteo, "_NORMALIZED_PATH", normalized)

    from_normalized = weather_openmeteo.load_weather_2025()
    assert from_normalized["temp_max"].tolist() == [1.3]

    normalized.unlink()
    from_raw = weather_openmeteo.load_weather_2025()
    pd.testing.assert_frame_equal(from_raw, from_normalized)


def test_traffic_prefers_normalized_then_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _write(tmp_path / "traffic_osm_moscow.json", {"_points": TRAFFIC_POINTS})
    normalized = _write(
        tmp_path / "normalized" / "traffic.json", {"rows": TRAFFIC_POINTS}
    )
    monkeypatch.setattr(traffic_osm, "_CATALOG_PATH", raw)
    monkeypatch.setattr(traffic_osm, "_NORMALIZED_PATH", normalized)

    points = traffic_osm.load_traffic_catalog()
    assert [p["id"] for p in points] == ["t1"]
    feats_from_normalized = traffic_osm.get_traffic_features(55.75, 37.61)

    normalized.unlink()
    assert [p["id"] for p in traffic_osm.load_traffic_catalog()] == ["t1"]
    assert traffic_osm.get_traffic_features(55.75, 37.61) == feats_from_normalized


def test_poi_and_stops_prefer_normalized_then_fall_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_poi = _write(tmp_path / "poi_moscow.json", POIS)
    raw_stops = _write(tmp_path / "stops_routes.json", {"_comment": "c", **STOPS})
    norm_poi = _write(tmp_path / "normalized" / "poi.json", {"rows": POIS})
    norm_stops = _write(tmp_path / "normalized" / "stops.json", {"routes": STOPS})
    monkeypatch.setattr(poi_features, "_POI_JSON", raw_poi)
    monkeypatch.setattr(poi_features, "_STOPS_JSON", raw_stops)
    monkeypatch.setattr(poi_features, "_POI_NORMALIZED", norm_poi)
    monkeypatch.setattr(poi_features, "_STOPS_NORMALIZED", norm_stops)

    assert poi_features.load_poi_catalog()[0]["name"] == "МГУ"
    assert poi_features.load_stops_catalog()[1][0]["name"] == "Чертаново"

    norm_poi.unlink()
    norm_stops.unlink()
    assert poi_features.load_poi_catalog()[0]["name"] == "МГУ"
    assert poi_features.load_stops_catalog()[1][0]["name"] == "Чертаново"


def test_events_prefers_normalized_then_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _write(tmp_path / "events_moscow.json", {"_comment": "c", "_events": EVENTS})
    normalized = _write(tmp_path / "normalized" / "events.json", {"rows": EVENTS})
    monkeypatch.setattr(events_calendar, "_EVENTS_JSON", raw)
    monkeypatch.setattr(events_calendar, "_EVENTS_NORMALIZED", normalized)

    assert events_calendar.load_events()[0]["id"] == "e1"

    normalized.unlink()
    assert events_calendar.load_events()[0]["id"] == "e1"


def test_validators_prefer_normalized_then_fall_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv = tmp_path / "validators_lookup.csv"
    csv.write_text(
        "route_id,weekday,hour,n_validators_mean,n_trams_mean\n1,0,0,2.0,1.0\n",
        encoding="utf-8",
    )
    normalized = _write(
        tmp_path / "normalized" / "validators.json", {"rows": VALIDATOR_ROWS}
    )
    monkeypatch.setattr(validators_lookup, "_CACHE_PATH", csv)
    monkeypatch.setattr(validators_lookup, "_NORMALIZED_PATH", normalized)

    from_normalized = validators_lookup.load_validators_lookup()
    assert from_normalized["route_id"].tolist() == [1]

    normalized.unlink()
    from_raw = validators_lookup.load_validators_lookup()
    pd.testing.assert_frame_equal(from_raw, from_normalized)
