"""Weather from Open-Meteo (T-161).

Кэширует CSV из archive-api.open-meteo.com для Москвы на весь 2025 год.
Колони: temp_max, temp_min, precipitation_sum, snowfall_sum, wind_speed_max.

Open-Meteo — бесплатный, без ключа, R4 hackathon-rules compliant
(скачиваем ОДИН раз, потом читаем CSV).

Покрытие: 2025-01-01 ... 2025-12-31 (включает train + holdout + submission).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

__all__ = ["get_weather_features", "get_weather_for_date", "load_weather_2025"]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CACHE_PATH = _REPO_ROOT / "data" / "external" / "weather_2025.csv"


def _ensure_cache() -> Path:
    """Убедиться, что CSV кэш существует."""
    if not _CACHE_PATH.exists():
        raise FileNotFoundError(
            f"Weather cache not found: {_CACHE_PATH}. "
            f"Run: curl 'https://archive-api.open-meteo.com/v1/archive?"
            f"latitude=55.7558&longitude=37.6173&start_date=2025-01-01"
            f"&end_date=2025-12-31&daily=temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,snowfall_sum,wind_speed_10m_max"
            f"&timezone=Europe/Moscow' > {_CACHE_PATH}"
        )
    return _CACHE_PATH


def load_weather_2025() -> pd.DataFrame:
    """Загрузить DataFrame с погодой на 2025 год.

    Returns:
        DataFrame с колонками: date, temp_max, temp_min, precipitation_sum,
        snowfall_sum, wind_speed_max.
    """
    path = _ensure_cache()
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def get_weather_for_date(d: date) -> dict[str, Any]:
    """Получить погоду на конкретную дату.

    Returns:
        dict с колонками погоды (без date).
    """
    df = load_weather_2025()
    row = df[df["date"] == d]
    if row.empty:
        # Fallback: ближайшая доступная дата
        return {
            "temp_max": 0.0,
            "temp_min": 0.0,
            "precipitation_sum": 0.0,
            "snowfall_sum": 0.0,
            "wind_speed_max": 0.0,
        }
    r = row.iloc[0]
    return {
        "temp_max": float(r["temp_max"]),
        "temp_min": float(r["temp_min"]),
        "precipitation_sum": float(r["precipitation_sum"]),
        "snowfall_sum": float(r["snowfall_sum"]),
        "wind_speed_max": float(r["wind_speed_max"]),
    }


def get_weather_features(d: date) -> dict[str, Any]:
    """Алиас для get_weather_for_date (для консистентности с seasonal_calendar)."""
    return get_weather_for_date(d)
