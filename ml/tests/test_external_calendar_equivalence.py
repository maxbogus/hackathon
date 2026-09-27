"""RED-тесты: календарь из `normalized/calendar.json` == hardcode в коде.

Шаг 0 (T-231): праздники/каникулы становятся данными (JSON), а не кодом.
Тест доказывает эквивалентность и наличие raw-фолбэка.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from transit_ai.data import calendar_rf, seasonal_calendar


def _write(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_calendar_from_json_matches_hardcode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holidays = sorted(d.isoformat() for d in calendar_rf.RF_HOLIDAYS_2025)
    breaks = [
        [start.isoformat(), end.isoformat()]
        for start, end in seasonal_calendar.SCHOOL_BREAKS
    ]
    normalized = _write(
        tmp_path / "calendar.json",
        {"source": "calendar", "holidays": holidays, "school_breaks": breaks},
    )
    monkeypatch.setattr(calendar_rf, "_NORMALIZED_PATH", normalized)
    monkeypatch.setattr(seasonal_calendar, "_NORMALIZED_PATH", normalized)

    assert calendar_rf._load_holidays() == set(calendar_rf.RF_HOLIDAYS_2025)
    assert seasonal_calendar._load_school_breaks() == list(
        seasonal_calendar.SCHOOL_BREAKS
    )

    # публичное поведение не меняется
    assert calendar_rf.is_holiday(min(calendar_rf.RF_HOLIDAYS_2025)) is True
    assert (
        seasonal_calendar.is_school_break(seasonal_calendar.SCHOOL_BREAKS[0][0]) is True
    )


def test_calendar_falls_back_to_hardcode_without_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        calendar_rf, "_NORMALIZED_PATH", tmp_path / "missing_calendar.json"
    )
    monkeypatch.setattr(
        seasonal_calendar, "_NORMALIZED_PATH", tmp_path / "missing_calendar.json"
    )

    assert calendar_rf._load_holidays() == set(calendar_rf.RF_HOLIDAYS_2025)
    assert seasonal_calendar._load_school_breaks() == list(
        seasonal_calendar.SCHOOL_BREAKS
    )
