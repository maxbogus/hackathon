"""Tests for weather_openmeteo.py (T-161)."""
from __future__ import annotations

from datetime import date

import pandas as pd

from transit_ai.data.weather_openmeteo import (
    load_weather_2025,
    get_weather_for_date,
    get_weather_features,
)


def test_load_weather_2025_returns_365_rows() -> None:
    """T-161: 365 дней погоды в кэше."""
    w = load_weather_2025()
    assert w.shape[0] >= 365
    assert "temp_max" in w.columns
    assert "temp_min" in w.columns
    assert "precipitation_sum" in w.columns
    assert "snowfall_sum" in w.columns


def test_get_weather_for_date_returns_row() -> None:
    """T-161: get_weather_for_date(2025-11-04) — день народного единства."""
    w = get_weather_for_date(date(2025, 11, 4))
    assert "temp_max" in w
    assert "temp_min" in w


def test_get_weather_features_returns_nov_dec() -> None:
    """T-161: features для ноября-декабря (submission period)."""
    for d in pd.date_range("2025-11-01", "2025-12-31"):
        feats = get_weather_features(d.date())
        assert "temp_max" in feats
        assert "temp_min" in feats
        assert "precipitation_sum" in feats
        assert "snowfall_sum" in feats
        assert "wind_speed_max" in feats
