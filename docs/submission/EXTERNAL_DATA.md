# EXTERNAL_DATA — пайплайн внешних данных (шаг 0, T-231)

> Как внешние источники превращаются в данные для обучения: **одна команда**,
> детерминированно, с sha256-манифестом. Закрывает критерий 2 жюри
> («внешние источники + воспроизводимый пайплайн приёма данных»).

## TL;DR

```bash
make external-gen      # raw → data/external/normalized/*.json + manifest.json
make external-verify   # sha256 + rows_count + JSON Schema (exit 1 при расхождении)
make external-show     # таблица: источник / строк / sha256 / потребитель
make external-all      # gen + verify
make external-fetch    # обновить raw из API (dev only, требует интернет — R4)
```

## Поток данных

```
внешние источники                raw (comмитим)                    normalized (коммитим)         потребители
─────────────────                ──────────────                    ─────────────────────         ───────────
Open-Meteo archive   ─┐   data/external/weather_2025.csv   →  normalized/weather.json    →  ml/…/weather_openmeteo.py
OSM Overpass (roads) ─┤   data/external/traffic_osm_moscow.json → normalized/traffic.json →  ml/…/traffic_osm.py
OSM Overpass + разметка → data/external/poi_moscow.json      →  normalized/poi.json        →  ml/…/poi_features.py
KudaGo-дамп (офлайн) ─┤   data/external/events_moscow.json  →  normalized/events.json     →  ml/…/events_calendar.py
разметка остановок   ─┤   data/external/stops_routes.json  →  normalized/stops.json      →  ml/…/poi_features.py + backend /api/v1/geo/routes
lib holidays + ПП РФ ─┤   data/external/holidays_ru_2025.json → normalized/calendar.json →  ml/…/calendar_rf.py
школьный календарь   ─┤   data/external/school_breaks_2025.json → (тот же calendar.json) →  ml/…/seasonal_calendar.py
производное (train.csv) → data/external/validators_lookup.csv → normalized/validators.json → ml/…/validators_lookup.py
user-разметка маршрутов → ml/…/_user_routes_2025.json        →  normalized/user_routes.json → ml/…/spravochnik_geo.py
```

Код ETL: `apps/harvester/app/build/` (builders → pipeline → cli). ML-слой **не** парсит
raw сам: он читает `normalized/*.json`, а raw остаётся фолбэком (если ETL не запускался).

## Как получать источники (ссылки)

| # | Источник | Как получить | Эффект на платформе |
|---|---|---|---|
| 1 | Погода — Open-Meteo Historical (бесплатно, без ключа, CC-BY) | `make external-fetch` или GET `https://archive-api.open-meteo.com/v1/archive?latitude=55.7558&longitude=37.6173&start_date=2025-01-01&end_date=2025-12-31&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_10m_max&timezone=Europe/Moscow` | вкл. по умолчанию; вклад в пределах шума |
| 2 | Дорожный трафик — OSM Overpass (ODbL) | POST `https://overpass-api.de/api/interpreter`, запрос в `EXTERNAL_SOURCES.md` | выкл. по умолчанию (на holdout ухудшал) |
| 3 | Сезонность/календарь — lib `holidays==0.55` + ПП РФ о переносах + школьный календарь Москвы (myschool.moscow) | export в `holidays_ru_2025.json` / `school_breaks_2025.json`; переносы и каникулы — из открытых календарей | **подтверждённый лифт** (праздничные множители, +0.013 п.п.) |
| 4 | POI/инфраструктура — OSM Overpass + ручная разметка 146 объектов / 13 категорий | `poi_moscow.json` (в git) | **подтверждённый лифт** (+0.013 п.п.) |
| 5 | События — дамп KudaGo/Wikipedia (офлайн, R4) | `events_moscow.json` (в git) | нейтрально (после blend) |

**Честная оговорка:** `validators_lookup.csv` — **производный** признак (агрегация
`data/real/train.csv` по `route × weekday × hour`), а не внешний источник. Агрегация
выполняется ML-модулем (pandas), ETL её только нормализует.

## Что гарантирует ETL

| Гарантия | Как проверяется |
|---|---|
| Детерминизм (два прогона → одинаковый артефакт) | `test_output_hashes_stable_across_two_runs` |
| Целостность (артефакт не менялся после сборки) | `make external-verify` (sha256 против `manifest.json`) |
| Совпадение количества строк | `rows_count == len(rows)` в verify |
| Контракт артефакта | `docs/schemas/external_dataset.schema.json` (draft-07) |
| Отсутствие сети в offline-режиме (R4) | `test_offline_mode_makes_no_network_calls` (httpx падает при обращении) |
| Метрики моделей не изменились | `ml/tests/test_external_raw_vs_normalized_equivalence.py` (raw == normalized) |

## Город-агностик / перенос

Добавление нового внешнего источника = 
1) положить raw в `data/external/` и добавить запись в `RAW_SOURCES` (`app/build/builders.py`);
2) написать builder (образец: `build_weather`) + RED-тест;
3) `make external-all` → нормализованный артефакт с sha256 в манифесте;
4) читать артефакт в ML-признаках (normalized первым, raw — фолбэк).

## Ограничения

- `data/real/train.csv` (9.7 ГБ) ETL не читает — производные артефакты собираются
  ML-модулем, ETL только нормализует результат.
- `external-fetch` (online) — только для dev: R4 запрещает сеть в runtime, поэтому
  коммитим raw-снимок, а не ходим в API на инференсе.
- Полные sha256 — в `data/external/normalized/manifest.json` (в этом документе —
  первые 8 символов для читаемости).
