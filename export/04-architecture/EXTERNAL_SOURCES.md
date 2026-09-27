# EXTERNAL_SOURCES — Внешние данные Transit-AI

> Создано в рамках критерия 2.a жюри (внешние источники, до 4 баллов).
> Каждый источник: ссылка/способ получения + эффект на платформенный score.

## Краткая сводка

| # | Источник | Файл | Эффект |
|---|---|---|---|
| 1 | Погода (Open-Meteo) | `data/external/weather_2025.csv` | T-160, ON по умолчанию |
| 2 | Трафик (OSM) | `data/external/traffic_osm_moscow.json` | T-124, OFF по умолчанию |
| 3 | Сезон/календарь (holidays) | `data/external/holidays_ru_2025.json` + lib `holidays==0.55` | T-148, ON, lift +0.013pp |
| 4 | POI (OSM + ручной) | `data/external/poi_moscow.json` | T-168, ON, lift +0.013pp |

---

## 1. Погода — Open-Meteo Historical

API: `https://archive-api.open-meteo.com/v1/archive?latitude=55.75&longitude=37.62&start_date=2025-01-01&end_date=2025-12-31&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_max&timezone=Europe/Moscow`

Хардкодед CSV в `data/external/weather_2025.csv` (365 строк, 6 колонок):
```
date,temp_max,temp_min,precipitation_sum,snowfall_sum,wind_speed_max
2025-01-01,1.3,-6.8,3.9,2.66,19.8
...
```

Используется: `ml/transit_ai/data/weather_openmeteo.py` (T-123). `use_weather=True` в seed.

Fallback: OpenWeatherMap Historical (платный), NOAA GHCN (только США).

---

## 2. Дорожный трафик — OSM Overpass

API: `https://overpass-api.de/api/interpreter` с запросом:
```
[out:json][timeout:60];
(way["highway"~"primary|secondary|tertiary"](55.5,37.3,55.9,37.9););
out tags;
```

Хардкодед JSON в `data/external/traffic_osm_moscow.json` (41 точка, 4 категории):
```json
{
  "_categories": {"major_arterial": "6+ полос (Тверская, Ленинский)"},
  "_points": [
    {"lat": 55.7615, "lon": 37.6105, "category": "major_arterial", "jam_level": 4}
  ]
}
```

Используется: `ml/transit_ai/data/traffic_osm.py` (T-124). `use_traffic=False` (holdout негативный).

Fallback: Яндекс.Пробки API (платный), TomTom Historical.

---

## 3. Сезонность + календарь — holidays lib + ручной каталог

Источник: Python lib `holidays==0.55` (https://pypi.org/project/holidays/) — 365 дней RU праздников.
+ ручной каталог школьных каникул (T-148).

Хардкодед JSON (генерируется `ml/transit_ai/data/seasonal_calendar.py`):
```json
[
  {"date": "2025-01-01", "kind": "holiday", "name": "Новый год", "weight": 0.5},
  {"date": "2025-11-04", "kind": "holiday", "name": "День народного единства", "weight": 0.7}
]
```

Используется: `ml/transit_ai/data/seasonal_calendar.py` (T-148). `use_seasonal=True`. F-082/F-083: holiday override ×0.5 для 3 и 4 ноября → lift +0.013pp.

Fallback: productioncalendar.ru API, isdayoff.ru.

---

## 4. POI / инфраструктура — OSM Overpass + ручной каталог

API: Overpass с тегами:
```
node["amenity"~"school|university|hospital"](55.5,37.3,55.9,37.9);
way["leisure"="park"](55.5,37.3,55.9,37.9);
```

Wiki: https://wiki.openstreetmap.org/wiki/Map_Features

Хардкодед JSON: `data/external/poi_moscow.json` (146 объектов, 13 категорий, ручная разметка T-168):
```json
[
  {"name": "МГУ им. Ломоносова", "category": "university", "lat": 55.7038, "lon": 37.5306},
  {"name": "Парк Горького", "category": "park", "lat": 55.7297, "lon": 37.6013}
]
```

Используется: `ml/transit_ai/data/poi_features.py` (T-168). `use_poi=True`. F-083: lift +0.013pp (0.82121 → 0.83455).

Fallback: 2GIS API (бесплатно до 1000/день), Яндекс.Карты POI.

---

## Как обновлять

R4 hackathon-rules: no runtime HTTP. Обновление вручную или через `make pipeline-fetch` в dev.

```bash
# 1. Скачать (online mode, dev only):
HARVESTER_MODE=online make pipeline-fetch

# 2. Валидировать:
uv run python scripts/validate_external.py

# 3. Обновить feature_toggles если новый источник
# 4. Переобучить: make train-xgboost
```

---

## Privacy & licensing

- OpenStreetMap (ODbL), Open-Meteo (CC-BY), holidays (MIT) — открытые данные.
- **no-PII** — только агрегированные данные + метаданные. ФЗ-152 compliant.

---

## Cross-references

- `ml/transit_ai/data/{weather_openmeteo,traffic_osm,seasonal_calendar,poi_features,events_calendar}.py`
- `data/external/*.json` + `.csv` — все источники
- `.clinerules/05-hackathon-rules.md` R4
- T-202 (этот ticket)
