---
id: T-123
phase: 1
title: интеграция погодных данных Open-Meteo (исторические + прогноз) как exogenous feature
priority: P1
effort: 3
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.8
  score: 2.67
depends_on: []
blocks: [T-125, T-126]
tags: [data, exogenous, weather, ml]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-123: интеграция погодных данных Open-Meteo (исторические + прогноз) как exogenous feature

## Context

Погода влияет на пассажиропоток: дождь/снег → больше людей в транспорте, сильный мороз →
меньше поездок. Из анализа: «без exogenous features — статистическая экстраполяция, с ними —
понимание физики».

Open-Meteo — бесплатный API без ключа (важно для R4 hackathon-rules «no internet at runtime»,
но для batch-прогноза и для разработки — ок).

## Acceptance Criteria

- [ ] Модуль `ml/transit_ai/data/weather.py` с функциями:
  - `fetch_historical_weather(lat, lon, start, end) -> pd.DataFrame`
  - `fetch_forecast_weather(lat, lon, hours_ahead) -> pd.DataFrame`
- [ ] Использует `https://archive-api.open-meteo.com/v1/archive` (история)
- [ ] Использует `https://api.open-meteo.com/v1/forecast` (прогноз)
- [ ] Hourly fields: `temperature_2m, precipitation, rain, snowfall, wind_speed_10m, weather_code`
- [ ] Кэширование в `data/external/weather_<lat>_<lon>.parquet` (чтобы не дёргать API повторно)
- [ ] Fallback на средние значения если API недоступен
- [ ] Lat/lon для Москвы: 55.7558, 37.6173 (центр)
- [ ] Unit-тест с mock httpx: `test_weather.py` (5+ кейсов: empty, normal, network error)

## Technical Notes

```python
import httpx
import pandas as pd
from pathlib import Path

CACHE_DIR = Path("data/external")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_historical_weather(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    cache_path = CACHE_DIR / f"weather_{lat:.2f}_{lon:.2f}_{start}_{end}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": "temperature_2m,precipitation,rain,snowfall,wind_speed_10m,weather_code",
        "timezone": "Europe/Moscow",
    }
    r = httpx.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["hourly"])
    df.to_parquet(cache_path)
    return df
```

Преобразование weather_code в категории:
- 0: clear
- 1-3: partly_cloudy
- 45-48: fog
- 51-67: rain
- 71-77: snow
- 80-82: heavy_rain
- 95-99: thunderstorm

## Verification

```bash
uv run pytest ml/tests/test_weather.py -v
# 5+ тестов зелёные

# Real test (нужен internet)
uv run python -c "from transit_ai.data.weather import fetch_historical_weather; df = fetch_historical_weather(55.75, 37.62, '2025-09-01', '2025-09-30'); print(df.shape, df.columns.tolist())"
# Должно вернуть (720, 7) — 30 дней * 24 часа = 720 строк
```

## Beneficiary Impact

**Город (⭐⭐⭐)** — exogenous features повышают точность модели → лучшие решения.
**Департамент** — feature engineering = production-ready, не игрушечный ML.

RICE: 2.67 — средний. Делается в Фазе 1.
