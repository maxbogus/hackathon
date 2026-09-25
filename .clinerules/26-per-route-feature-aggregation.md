# 26-per-route-feature-aggregation.md — агрегация per-stop → per-route

## Проблема

В проекте Transit-AI XGBoostRoutePredictor работает с **route-only данными**:
`[route_id, date, hour, boardings]`. Это осознанное решение (F-020): stop_id в фичах
вызывает overfitting (модель запоминает конкретные остановки, плохо генерализует
на ноябрь-декабрь, когда boardings per stop могут отличаться).

Но многие фичи **географически привязаны к остановке**, не к маршруту:
- POI (школы/вузы/ТЦ рядом)
- Расстояние до метро
- Количество пересадок
- Density населения

Если просто использовать per-stop фичи → нужен stop_id в train → overfitting (F-020).
Если игнорировать → теряем географический сигнал.

## Правило (из D-025)

**Географические фичи агрегируются per-stop → per-route через `mean`**:

```python
# ml/transit_ai/models/xgboost_route.py:220-234
for rid in df["route_id"].astype(int).unique():
    poi_df = get_route_poi_features(int(rid))  # per-stop DataFrame
    if not poi_df.empty:
        poi_cache[int(rid)] = poi_df.mean(numeric_only=True).to_dict()
```

Это даёт **одну фичу на route_id** (например, `n_universities_1500m = среднее
число университетов в 1.5km по всем остановкам маршрута`).

## Когда применять

| Ситуация | Агрегация |
|---|---|
| Per-stop фичи (POI, расстояния) + route-only данные | `mean` (default) |
| Per-stop фичи + stop-level данные (есть stop_id в train) | per-row без агрегации |
| Per-time фичи (час пик × route) + route-only данные | уже per-row, не агрегируется |
| Per-day фичи (погода, события) + route-only данные | уже per-row, не агрегируется |

## Альтернативы (и почему отклонены)

| Метод | Почему нет |
|---|---|
| `max` (макс POI на маршруте) | Теряется информация о средней плотности |
| `min` | То же + outlier-чувствительность |
| `weighted_mean` по координатам | Complexity без подтверждённого выигрыша |
| `weighted_mean` по passenger volume | Нет stop-level boardings для весов |
| `median` | Robust к outliers, но mean проще и понятнее для XGBoost |

## Когда пересмотреть

- Появились **stop-level данные** в train (открыли доступ к валидациям по остановкам)
- Per-route mean дал **нулевой feature importance** в XGBoost → возможно per-stop лучше
- Per-route mean **работает отлично** → значит география не зависит от остановки внутри маршрута

## Cross-references

- D-025 в `docs/ledger/decisions.jsonl` — обоснование mean агрегации
- F-020 в `docs/ledger/findings.jsonl` — почему route-only данные
- T-168 — тикет, в котором это правило появилось
- `ml/transit_ai/models/xgboost_route.py:220-234` — реализация

## Расширение: weighted mean (когда появится stop-level data)

Если в будущем получим boardings per stop:

```python
def weighted_mean_per_route(per_stop_df, weights_by_stop):
    """weights_by_stop: dict[stop_name, total_boardings_from_train]"""
    weighted_sum = sum(per_stop_df[stop] * weights_by_stop.get(stop, 1) 
                       for stop in per_stop_df.index)
    total_weight = sum(weights_by_stop.get(stop, 1) for stop in per_stop_df.index)
    return weighted_sum / total_weight
```

Но **только если будет доказано** что weighted_mean лучше обычного mean на holdout.
Иначе — YAGNI.
