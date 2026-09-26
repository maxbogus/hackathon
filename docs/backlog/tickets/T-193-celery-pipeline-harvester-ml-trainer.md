---
id: T-193
phase: 3
title: Celery pipeline (harvester + ml-trainer) через Docker
priority: P0
effort: 4
unit: hours
rice:
  R: 4
  I: 2
  C: 0.9
  score: 1.80
depends_on: [T-143]
blocks: [T-194, T-195, T-196]
tags: [pipeline, celery, docker, backend, ml, infrastructure]
status: done
created: 2026-09-26
updated: 2026-09-26
assignee: ""
---

## Context

Архитектурное требование: данные качаются в JSON тулой (Docker+Celery),
затем другой Celery worker делает модель/модели, всё пишется в БД,
интерфейс читает из БД. Без этого компонента frontend не имеет исторических
данных и актуальных прогнозов, критерии 2-4 жюри (п.5 "Дополнительные
возможности") не закрываются.

## Acceptance Criteria

- [x] Создан `apps/harvester/` (Celery worker для сбора JSON)
- [x] Создан `apps/ml_pipeline/` (Celery worker для train + predict)
- [x] `pyproject.toml` обновлён: workspace members + sources
- [x] Dockerfiles для обоих workers (multi-stage, uv 0.5.7, non-root)
- [x] `docker-compose.yml` расширен профилем `pipeline`
- [x] Makefile: `pipeline-up / down / logs / fetch / train / predict / full / test`
- [x] 7 unit тестов harvester (weather/traffic/poi/events + dual-schema support)
- [x] 3 smoke теста ml_pipeline
- [x] Harvester в local mode читает из `data/external/*.json` (R4 safe)
- [x] Harvester в online mode ходит в Open-Meteo + OSM Overpass
- [x] ruff check: 0 errors на новых файлах

## Technical Notes

### Harvester tasks (apps/harvester/app/tasks.py)

- `fetch_weather_json(lat, lon, start_date, end_date)` — Open-Meteo archive API
- `fetch_traffic_json()` — OSM Overpass API (highway=primary/secondary)
- `fetch_poi_json()` — POI (школы/вузы/ТЦ) из OSM
- `fetch_events_json()` — календарь событий (T-172)
- `fetch_all()` — все выше + агрегированный результат

### ML Pipeline tasks (apps/ml_pipeline/app/tasks.py)

- `train_xgboost_task(model_id)` — обёртка над `ml/scripts/train_xgboost.py`
- `predict_window_task(model_id, start_date, end_date, coef_*, zeros)` — обёртка над `make_submission.py`
- `full_pipeline(...)` — train → predict последовательно
- `_persist_predictions_to_db()` — stub для T-194

### Docker

- Профиль `pipeline` поднимает обоих workers + использует Redis broker (db=1)
- ML pipeline ждёт `postgres:healthy` (для будущего T-194)

### Поддержка схем external JSON

```python
# traffic_osm_moscow.json: ключи "elements" (Overpass) или "_points" (T-124)
# events_moscow.json: ключи "events" или "_events" (T-172)
# poi_moscow.json: ключи "pois" (T-168)
```

## Verification

```bash
# 1. Tests
make pipeline-test
# → 7 passed (harvester) + 3 passed (ml_pipeline)

# 2. Smoke run harvester (без брокера)
make pipeline-fetch
# → {"status": "ok", "results": {weather: 365, traffic: 41, poi: 146, events: 8}}

# 3. Validate compose config
docker compose --profile pipeline config | grep -A 2 harvester

# 4. Lint
uv run ruff check apps/harvester/ apps/ml_pipeline/
# → All checks passed!
```

## Status

`done` (RED→GREEN→REFACTOR завершён в этой сессии)
