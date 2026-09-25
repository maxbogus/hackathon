# Skill: POI feature engineering для трамвайных маршрутов

Использовать через `use_skill("poi-feature-engineering")` при работе над
тикетами типа T-168 (POI features), или когда нужно добавить геопространственные
фичи в модель Transit-AI.

## Контекст

**POI (Points of Interest)** — объекты вокруг маршрута, влияющие на пассажиропоток:
школы, вузы, ТЦ, стадионы, театры, парки, метро, вокзалы, больницы, рынки.

Модель XGBoostRoutePredictor работает с route-only данными (F-020: stop_id вызывает
overfitting). Нужно преобразовать geo-данные в per-route фичи через агрегацию (D-025).

## Пошаговая инструкция

### Шаг 1: Собрать POI каталог

**Формат:** `data/external/poi_<scope>.json`
```json
[
  {"name": "МГУ им. Ломоносова", "category": "university", "lat": 55.7038, "lon": 37.5306},
  {"name": "Стадион Лужники",     "category": "stadium",     "lat": 55.7155, "lon": 37.5536}
]
```

**Обязательные поля:** `name` (str), `category` (str), `lat` (float), `lon` (float)
**Валидация:** name непустой, lat ∈ [55.0, 56.0] (Москва), lon ∈ [37.0, 38.0]

**Источники (по приоритету):**
1. Пользовательская разметка (per-route, точные координаты) — самый ценный источник
2. Открытые источники (Wikipedia, OpenStreetMap, Яндекс.Карты)
3. НЕ использовать Overpass API напрямую (R4 hackathon-rules: no internet at runtime)

### Шаг 2: Собрать каталог остановок

**Формат:** `data/external/stops_routes.json`
```json
{
  "_comment": "...",
  "26": [
    {"name": "Метро Университет", "lat": 55.6925, "lon": 37.5345},
    {"name": "Октябрьская", "lat": 55.7305, "lon": 37.6110}
  ]
}
```

**Структура:** dict[route_id (int, как str)] → list[{name, lat, lon}]
**Валидация:** все 10 маршрутов (1, 5, 7, 11, 12, 17, 25, 26, 28, 50), ≥ 5 остановок/маршрут

### Шаг 3: Определить категории и радиусы

См. `.clinerules/25-poi-radius-selection.md`. Per-category радиусы подбираются
по реальным расстояниям от остановок до ближайших объектов категории.

**Шаблон:**
```python
CATEGORY_RADIUS_KM: dict[str, float] = {
    "school": 0.5,      # плотная сеть
    "clinic": 0.5,
    "university": 1.5,  # крупные, разбросаны
    "stadium": 1.5,
    "hospital": 1.5,
    "park": 1.0,        # средние
    "mall": 1.0,
    # ...
}
```

### Шаг 4: Реализовать per-stop POI функции

```python
# ml/transit_ai/data/poi_features.py
from transit_ai.data.spravochnik_geo import _haversine_km

def count_poi_for_stop(lat, lon, category, radius_km=None):
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    if radius_km is None:
        radius_km = CATEGORY_RADIUS_KM[category]
    catalog = load_poi_catalog()
    return sum(1 for p in catalog
               if p["category"] == category
               and _haversine_km(lat, lon, p["lat"], p["lon"]) <= radius_km)

def get_stop_poi_features(lat, lon):
    feats = {}
    for cat in VALID_CATEGORIES:
        feats[_column_name(cat, CATEGORY_RADIUS_KM[cat])] = count_poi_for_stop(lat, lon, cat)
    feats["dist_to_nearest_metro_km"] = dist_to_nearest(lat, lon, "metro_hub")
    feats["poi_score"] = sum(feats.values())
    return feats
```

### Шаг 5: RED-тесты (ДО реализации)

```python
def test_count_university_near_metro_universitet():
    n = count_poi_for_stop(lat=55.6925, lon=37.5345, category="university")
    assert n >= 1

def test_get_stop_poi_features_has_n_features():
    feats = get_stop_poi_features(lat=55.6925, lon=37.5345)
    assert set(feats.keys()) == set(POI_FEATURE_NAMES)

def test_build_all_route_poi_features_shape():
    df = build_all_route_poi_features()
    assert df.shape[0] == 142  # 10 маршрутов × ~14 остановок
    assert df.shape[1] == 17  # 15 POI + route_id + stop_name
```

### Шаг 6: GREEN — реализация

Реализовать функции, прогнать тесты, добиться 100% pass.

### Шаг 7: Интеграция в XGBoostRoutePredictor

```python
# ml/transit_ai/models/xgboost_route.py
from transit_ai.data.poi_features import POI_FEATURE_NAMES, get_route_poi_features

_POI_FEATURES = tuple(POI_FEATURE_NAMES)

FEATURE_NAMES = (
    ...,
    *_POI_FEATURES,  # ПОСЛЕ _EXTERNAL_FEATURES, ДО lag features
    ...,
)

def _make_features(df):
    # ... geo + seasonal + weather + validators ...

    # T-168: POI per-route (mean по остановкам)
    poi_cache = {}
    for rid in df["route_id"].astype(int).unique():
        poi_df = get_route_poi_features(int(rid))
        poi_cache[int(rid)] = poi_df.mean(numeric_only=True).to_dict()

    for feat_name in POI_FEATURE_NAMES:
        df[feat_name] = df["route_id"].map(
            lambda r: poi_cache.get(int(r), {}).get(feat_name, 0.0)
        )
```

### Шаг 8: Train + Submission

```bash
uv --directory ml run python scripts/train_xgboost.py --model-id xgboost_v8_poi

uv --directory ml run python scripts/make_submission.py \
    --model-id xgboost_v8_poi \
    --submission-id v8-poi \
    --output $(git rev-parse --show-toplevel)/predictions/submission.csv
```

**⚠️ КРИТИЧНО**: --output должен быть **абсолютным путём от корня репо**
(`predictions/`), иначе скрипт создаст файлы в `ml/predictions/`. Это баг (F-035).

### Шаг 9: Manifest.json

**Обязательно** (R2 clinerule 23): `predictions/<csv_basename>.json` рядом с CSV.
Скрипт `make_submission.py` создаёт автоматически через `write_manifest()`.

## Типичные ошибки

1. **500m для всех категорий** — пропускаем крупные объекты (МГУ на 1.28km)
2. **Per-stop фичи без агрегации** — нужен stop_id, иначе модель не использует
3. **Overpass API в коде** — нарушает R4 (no internet at runtime)
4. **Relative --output** — файл попадает в `ml/predictions/` вместо `predictions/`
5. **POI без радиуса** — `radius_km=None` → default per category, **не** `1km` для всех

## Acceptance criteria шаблон

```markdown
- [ ] `data/external/poi_<scope>.json` создан (≥100 объектов, ≥10 категорий)
- [ ] `data/external/stops_routes.json` создан (все 10 маршрутов, ≥5 остановок/маршрут)
- [ ] `ml/transit_ai/data/poi_features.py` с API: load_poi_catalog, count_poi_for_stop, get_stop_poi_features
- [ ] `ml/tests/test_poi_features.py` ≥10 RED-then-GREEN тестов
- [ ] XGBoostRoutePredictor обновлён: POI_FEATURES в FEATURE_NAMES, расчёт в _make_features
- [ ] Train + submission прошли, holdout WAPE-score не хуже предыдущей версии
- [ ] Manifest рядом с CSV (R2 clinerule 23)
```

## Cross-references

- T-168 — тикет-шаблон
- D-024, D-025, D-026 — решения по POI radius / aggregation / hardcoded catalog
- F-033, F-034, F-035 — находки по WAPE-score / submission #8 / path bug
- `.clinerules/25-poi-radius-selection.md` — выбор радиуса
- `.clinerules/26-per-route-feature-aggregation.md` — per-route mean aggregation
- `.clinerules/27-wape-score-vs-wape.md` — интерпретация метрик

