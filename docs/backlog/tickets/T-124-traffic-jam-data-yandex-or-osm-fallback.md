---
id: T-124
phase: 1
title: интеграция данных о пробках (Яндекс.Пробки API или OSM fallback)
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
tags: [data, exogenous, traffic, ml]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-124: интеграция данных о пробках (Яндекс.Пробки API или OSM fallback)

## Context

Трамваи стоят в пробках из-за машин на путях — это влияет на ETA и загрузку (собранные
пассажиры за время ожидания). Из анализа: «Трамваи сильно зависят от дорожной ситуации.
Автомобили, выезжающие на трамвайные пути, создают заторы и сбивают весь график движения».

**Проблема:** Яндекс.Пробки API платный и может не быть ключа на хакатоне.
**Решение:** двухуровневая стратегия:
1. Если есть API ключ от орг. — использовать Яндекс.Пробки
2. Если нет — OpenStreetMap + overpass для структурных фичей (lane_count, has_tram_separation)

## Acceptance Criteria

- [ ] Модуль `ml/transit_ai/data/traffic.py` с функциями:
  - `fetch_yandex_traffic_archive(date) -> pd.DataFrame` (если есть ключ)
  - `fetch_osm_traffic_features(bbox) -> pd.DataFrame` (fallback)
- [ ] Яндекс.Пробки integration через Yandex.Maps JS API (headless, если нужно)
- [ ] OSM fallback через `osmnx` или `overpy` — получение дорожной сети Москвы
- [ ] Фичи из OSM: `is_main_road`, `lane_count`, `has_tram_lane`, `max_speed_kmh`
- [ ] Кэширование в `data/external/traffic_*.parquet`
- [ ] Конфиг через env: `YANDEX_MAPS_API_KEY` (если есть — используется, иначе OSM)
- [ ] Unit-тест с mock: `test_traffic.py`

## Technical Notes

```python
import os
import httpx
import pandas as pd
from pathlib import Path

CACHE_DIR = Path("data/external")

def fetch_traffic_features(bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """bbox = (lat_min, lon_min, lat_max, lon_max) для Москвы."""
    cache_path = CACHE_DIR / f"traffic_osm_{bbox}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    
    # OSM Overpass query
    query = """
    [out:json][timeout:60];
    (
      way["highway"~"primary|secondary|tertiary"]["tram"="yes"];
    );
    out tags;
    """
    # ... (используем overpy)
    # Парсим: lane_count, maxspeed, tram_lanes
    return df
```

bbox Москвы: `(55.55, 37.30, 55.92, 37.85)` (из `SyntheticConfig`).

Если `YANDEX_MAPS_API_KEY` в env — пробуем Яндекс.Пробки:
```python
if os.environ.get("YANDEX_MAPS_API_KEY"):
    return fetch_yandex_traffic(date)
return fetch_osm_traffic_features(bbox)
```

## Verification

```bash
uv run pytest ml/tests/test_traffic.py -v
# Тесты с mock должны быть зелёные

# Real test (нужен internet для OSM)
uv run python -c "from transit_ai.data.traffic import fetch_osm_traffic_features; df = fetch_osm_traffic_features((55.55, 37.30, 55.92, 37.85)); print(df.shape)"
```

## Beneficiary Impact

**Город (⭐⭐⭐)** — модель учитывает реальные задержки, не только расписание.
**Пассажиры (⭐⭐)** — точнее ETA = меньше разочарований от «опоздания на 15 мин».

RICE: 2.67 — средний. Делается в Фазе 1, можно отложить если времени нет.
