"""Регрессия: raw и normalized дают ИДЕНТИЧНЫЕ данные (шаг 0, T-231).

Это «предохранитель метрик»: если ETL начнёт терять колонки/поля, тест упадёт
до того, как поедут holdout-метрики. Требует сгенерированных артефактов
(`make external-gen`); иначе скипается.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from transit_ai.data import calendar_rf, seasonal_calendar

EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"
NORMALIZED = EXTERNAL / "normalized"

pytestmark = pytest.mark.skipif(
    not (NORMALIZED / "manifest.json").exists(),
    reason="normalized не сгенерирован: make external-gen",
)


def _artifact(name: str) -> dict:
    return json.loads((NORMALIZED / name).read_text(encoding="utf-8"))


def test_weather_normalized_equals_csv() -> None:
    raw = pd.read_csv(EXTERNAL / "weather_2025.csv")
    raw["date"] = pd.to_datetime(raw["date"]).dt.date

    normalized = pd.DataFrame(_artifact("weather.json")["rows"])
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.date

    pd.testing.assert_frame_equal(raw, normalized)


def test_poi_normalized_equals_raw() -> None:
    raw = json.loads((EXTERNAL / "poi_moscow.json").read_text(encoding="utf-8"))
    assert raw == _artifact("poi.json")["rows"]


def test_stops_normalized_equals_raw() -> None:
    raw = json.loads((EXTERNAL / "stops_routes.json").read_text(encoding="utf-8"))
    raw = {k: v for k, v in raw.items() if not str(k).startswith("_")}
    assert raw == _artifact("stops.json")["routes"]


def test_traffic_normalized_equals_points() -> None:
    raw = json.loads((EXTERNAL / "traffic_osm_moscow.json").read_text(encoding="utf-8"))
    assert raw["_points"] == _artifact("traffic.json")["rows"]


def test_events_normalized_equals_raw() -> None:
    raw = json.loads((EXTERNAL / "events_moscow.json").read_text(encoding="utf-8"))
    assert raw["_events"] == _artifact("events.json")["rows"]


def test_validators_normalized_equals_csv() -> None:
    raw = pd.read_csv(EXTERNAL / "validators_lookup.csv")
    normalized = pd.DataFrame(_artifact("validators.json")["rows"])
    pd.testing.assert_frame_equal(raw, normalized)


def test_calendar_normalized_equals_hardcode() -> None:
    assert calendar_rf._load_holidays() == set(calendar_rf.RF_HOLIDAYS_2025)
    assert seasonal_calendar._load_school_breaks() == list(
        seasonal_calendar.SCHOOL_BREAKS
    )
