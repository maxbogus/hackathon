---
id: T-125
phase: 1
title: feature engineering — добавить weather и traffic фичи в обучающую выборку
priority: P1
effort: 2
unit: hours
rice:
  R: 6
  I: 2.0
  C: 0.9
  score: 5.4
depends_on: [T-123, T-124]
blocks: [T-126]
tags: [ml, feature-engineering, exogenous]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-125: feature engineering — добавить weather и traffic фичи в обучающую выборку

## Context

T-123 (weather) и T-124 (traffic) дают exogenous данные в виде parquet. Этот тикет —
**склейка**: добавить новые фичи к существующему ridership DataFrame, чтобы XGBoost
мог их использовать при обучении и inference.

## Acceptance Criteria

- [ ] Модуль `ml/transit_ai/data/features.py` с функцией:
  - `add_exogenous_features(ridership_df, weather_df, traffic_df) -> pd.DataFrame`
- [ ] Merge по `timestamp` (hourly granularity)
- [ ] Новые колонки:
  - `temperature_c: float`
  - `precipitation_mm: float`
  - `is_rain: bool` (precipitation > 0)
  - `is_snow: bool` (snowfall > 0)
  - `weather_category: int` (0=clear, 1=cloudy, 2=rain, 3=snow, 4=storm)
  - `wind_speed_ms: float`
  - `traffic_jam_score: float` (0-10, из Яндекс.Пробки или OSM-derived)
  - `is_main_road: bool` (OSM)
- [ ] NaN handling: заполнение медианой для числовых, mode для категориальных
- [ ] Без breaking changes: существующие XGBoost/BaselineMean должны продолжать работать
- [ ] Unit-тест: `test_features.py` (5+ кейсов)

## Technical Notes

```python
import pandas as pd

def add_exogenous_features(
    ridership_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    traffic_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = ridership_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Merge weather (hourly)
    weather_df = weather_df.copy()
    weather_df["timestamp"] = pd.to_datetime(weather_df["time"])
    df = df.merge(
        weather_df[["timestamp", "temperature_2m", "precipitation", "snowfall", "wind_speed_10m", "weather_code"]],
        on="timestamp", how="left"
    )
    df = df.rename(columns={
        "temperature_2m": "temperature_c",
        "precipitation": "precipitation_mm",
        "wind_speed_10m": "wind_speed_ms",
    })
    
    # Derived features
    df["is_rain"] = (df["precipitation_mm"] > 0).astype(int)
    df["is_snow"] = (df["snowfall"] > 0).astype(int)
    df["weather_category"] = df["weather_code"].apply(_weather_to_category)
    
    # Traffic (optional)
    if traffic_df is not None:
        df = df.merge(traffic_df, on=["timestamp", "stop_id"], how="left")
        df["traffic_jam_score"] = df["traffic_jam_score"].fillna(5.0)  # median
    
    return df
```

Затем `XGBoostPredictor.fit()` обновляется:
```python
FEATURE_NAMES = (
    ...existing...,
    "temperature_c", "precipitation_mm", "is_rain", "is_snow",
    "weather_category", "wind_speed_ms", "traffic_jam_score",
)
```

## Verification

```bash
uv run pytest ml/tests/test_features.py -v
# Тесты на merge, NaN, derived features

# Smoke test
uv run python -c "
from transit_ai.data.features import add_exogenous_features
df = add_exogenous_features(ridership, weather)
print(df.columns.tolist())
print(df[['temperature_c', 'is_rain', 'weather_category']].head())
"
```

## Beneficiary Impact

**Город (⭐⭐⭐)** — модель становится точнее за счёт реальных физических факторов.
**Департамент** — feature engineering = production-ready ML, не статистическая экстраполяция.

RICE: 5.4 — топ-12. Делается в Фазе 1.
