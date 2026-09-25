---
id: T-168
phase: 2
title: POI features для маршрутов — schools/universities/stadiums/parks/malls/theaters (hardcoded Moscow)
priority: P1
effort: 3
unit: hours
rice:
  R: 8
  I: 2.0
  C: 0.7
  score: 3.73
depends_on: [T-156, T-160, T-161, T-162]
blocks: [T-169]
tags: [ml, feature-engineering, poi, route-context, gis]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-168: POI features для маршрутов (hardcoded Moscow)

## Context

T-160/T-161/T-162 добавили **календарные и погодные** фичи (school breaks,
weather, validators). Holdout WAPE_score улучшился 0.9030 → 0.9009 (+0.6pp),
platform WAPE поднялся до 0.15366. Это **временные** факторы.

Упускаем **географический контекст маршрута**: маршрут 26 (Университет →
Октябрьская) проходит мимо МГУ и Парка Горького — даже в обычные дни там
другой профиль пассажиропотока чем у спального маршрута 25. Сейчас модель
не различает "стадион рядом" от "пустырь".

**Решение:** 8 категориальных POI-фичей per route, посчитанных как
**count в радиусе от средней точки маршрута** (lat_mid, lon_mid из
`spravochnik_geo.py`). Источник POI — **hardcoded JSON** (`data/external/poi_moscow.json`)
с ~80 топ-POI Москвы рядом с трамвайными маршрутами.

Hardcoded, потому что:
1. **Никаких external API** (R4 hackathon-rules: no internet at runtime)
2. **Offline & reproducible** (R3: lockfile + git-tracked data)
3. **80 точек** покрывают топ-объекты в полосе трамвайных маршрутов
4. **Расширяемо**: формат JSON → позже T-169 добавит Overpass как opt-in

## Acceptance Criteria

- [ ] `data/external/poi_moscow.json` — список из ~80 POI:
  - [ ] Обязательные поля: `name` (str), `category` (school/university/stadium/park/mall/theater), `lat` (float), `lon` (float)
  - [ ] Покрывает все 10 маршрутов хакатона (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)
  - [ ] Комментарий в начале файла со списком источников (Wikipedia / 2GIS / Яндекс.Карты)
- [ ] `ml/transit_ai/data/poi_features.py` — модуль с:
  - [ ] `load_poi_catalog() -> list[dict]` — читает JSON, валидирует schema
  - [ ] `count_poi_in_radius(route_id: int, category: str, radius_km: float = 0.5) -> int`
  - [ ] `build_route_poi_features() -> pd.DataFrame` — для всех 10 маршрутов возвращает DataFrame с 8 колонками:
    - `n_schools_500m`, `n_universities_500m`, `n_stadiums_1km`,
    - `n_parks_500m`, `n_malls_500m`, `n_theaters_500m`,
    - `poi_density` (сумма всех 6 категорий),
    - `is_event_venue_route` (1 если есть stadium/theater/major_park в 1km)
  - [ ] Использует координаты из `_user_routes_2025.json` (lat_mid/lon_mid) + `spravochnik_geo.build_route_geo_features()`
- [ ] `ml/tests/test_poi_features.py` — **RED тесты** (до реализации):
  - [ ] `test_load_poi_catalog_returns_list`: JSON загружается, длина ≥ 50, все имеют required поля
  - [ ] `test_count_poi_in_radius_for_route_26`: route 26 имеет n_universities_500m ≥ 1 (МГУ рядом)
  - [ ] `test_count_poi_in_radius_for_route_50`: route 50 имеет n_theaters_500m ≥ 1 (центр)
  - [ ] `test_build_route_poi_features_shape`: DataFrame shape = (10, 8), все значения ≥ 0, dtype float
- [ ] `ml/transit_ai/models/xgboost_route.py`:
  - [ ] `_POI_FEATURES` tuple с 8 именами
  - [ ] `_POI_CACHE` ленивая загрузка
  - [ ] `_poi_for_route(route_id)` helper
  - [ ] `FEATURE_NAMES` расширен: `*_POI_FEATURES` после `*_EXTERNAL_FEATURES`
- [ ] Submission #8:
  - [ ] `make submission` → holdout WAPE_score + пометка в manifest
  - [ ] Цель: **≥0.9015** на holdout (vs текущие 0.9009)
  - [ ] Если лучше → коммит `feat(ml): POI features (T-168)` + push

## Technical Notes

**Структура POI каталога** (пример):
```json
[
  {"name": "МГУ им. Ломоносова", "category": "university", "lat": 55.7038, "lon": 37.5306},
  {"name": "Стадион Лужники",     "category": "stadium",     "lat": 55.7155, "lon": 37.5536},
  {"name": "Парк Горького",       "category": "park",        "lat": 55.7297, "lon": 37.6013},
  {"name": "ТЦ Атриум",           "category": "mall",        "lat": 55.7567, "lon": 37.5667},
  {"name": "Большой театр",       "category": "theater",     "lat": 55.7601, "lon": 37.6189}
]
```

**Алгоритм `count_poi_in_radius`:**
```python
def count_poi_in_radius(route_id: int, category: str, radius_km: float = 0.5) -> int:
    geo = build_route_geo_features()
    row = geo[geo["route"] == route_id].iloc[0]
    catalog = [p for p in load_poi_catalog() if p["category"] == category]
    n = 0
    for p in catalog:
        if haversine_km(row["lat_mid"], row["lon_mid"], p["lat"], p["lon"]) <= radius_km:
            n += 1
    return n
```

**Радиусы выбраны так:**
- `500m` (пешеходная доступность) — schools, parks, malls, theaters, universities
- `1km` (короткая поездка) — stadiums (их в Москве мало)

**Источники POI:**
- Wikipedia (список стадионов / парков / театров Москвы)
- 2GIS (категории организаций)
- Яндекс.Карты (для подтверждения координат)

## Verification

```bash
# 1. RED тесты падают
make ml-test TEST=tests/test_poi_features.py
# Expected: ModuleNotFoundError or 4 failures

# 2. Создать data/external/poi_moscow.json (≥80 POI)

# 3. GREEN: реализовать poi_features.py

# 4. Тесты зелёные
make ml-test TEST=tests/test_poi_features.py
# Expected: 4 passed

# 5. Интеграция в XGBoost
make train-xgboost
make predict
# → новый submission.csv + manifest

# 6. Holdout WAPE_score должен быть ≥ 0.9009 (или явное улучшение)
cat predictions/submission_manifest.json | jq .holdout_wape_score

# 7. Conventional Commit
git add ml/transit_ai/data/poi_features.py ml/tests/test_poi_features.py \
        data/external/poi_moscow.json ml/transit_ai/models/xgboost_route.py
git commit -m "feat(ml): POI features per route — schools/stadiums/parks (T-168)"
```

## Out of Scope

- ❌ Overpass API integration (отложено в T-169)
- ❌ Time-of-day POI variation (POI статичны для маршрута)
- ❌ Walking distance / routing (только haversine distance)
- ❌ Indoor POI (метро, ТЦ этажи)
- ❌ Per-direction POI (только mid-точка маршрута)

## Status

`ready` → `in-progress` → `done`
