# MODEL_DOMAIN — Область определения и адаптации модели

> Создано в рамках критерия 2.b жюри (область определения и адаптации, до 2 баллов).
> Определяет: на каких маршрутах/горизонтах/диапазонах данных модель валидна,
> как перенести на новые маршруты/периоды.

## Область определения (validity scope)

### Маршруты

Модель обучена на **10 маршрутах трамваев Москвы**:

| route_id | Статус |
|---|---|
| 1, 5, 7, 11, 12, 17, 25, 26, 28, 50 | ✅ Обучены |
| 5 (отдельно) | ⚠️ Zeroed (F-051: cold start) |

**10 × 61 день × 24 часа = 14 640 строк** в submission (F-045).

### Период

- **Train:** `2025-01-01 .. 2025-08-31`
- **Holdout:** `2025-09-01 .. 2025-10-31`
- **Submission:** `2025-11-01 .. 2025-12-31`

### Горизонты

| Horizon | Granularity | Модель | Status |
|---|---|---|---|
| `day` | `hour` | XGBoost, GRU | ✅ Best (F-083, 0.83455) |
| `month` | `day` | XGBoost + Hybrid | ✅ |
| `year` | `month` | Monte Carlo | ✅ |

### Внешние данные (зависимости)

| Зависимость | Файл |
|---|---|
| Open-Meteo weather | `ml/transit_ai/data/weather_openmeteo.py` (T-123) |
| OSM POI | `ml/transit_ai/data/poi_features.py` (T-168) |
| OSM traffic | `ml/transit_ai/data/traffic_osm.py` (T-124) |
| holidays (RU) | `ml/transit_ai/data/seasonal_calendar.py` (T-148) |
| events | `ml/transit_ai/data/events_calendar.py` (T-172) |

Подробнее: `docs/EXTERNAL_SOURCES.md`.

### Корректирующие коэффициенты (default = best)

`coef_weather = coef_event = coef_season = 1.0`
Zero overrides: `zero_route_5=ON`, `zero_night_pred_cap=ON (55, h0-4)`
Toggles: `use_poi/weather/events/seasonal/lag=ON`, `use_traffic=OFF`

---

## Пределы применимости (limits)

### Что модель НЕ делает

- ❌ Не предсказывает для других городов (Москва → Питер — нет данных)
- ❌ Не работает для новых маршрутов без ≥2 месяцев boardings (T-126)
- ❌ Не учитывает аварии/перекрытия в реальном времени (только hardcoded events)
- ❌ Не учитывает погодные аномалии (средние исторические)
- ❌ Не моделирует межмаршрутные пересадки (per-route isolation)

### Неопределённости (F-NNN)

| Источник | F |
|---|---|
| Drift local vs platform | F-040 (-0.05..-0.14pp) |
| Route 5 cold start | F-051 (zeroed) |
| Holidays impact | F-080 (×0.5, +0.013pp) |
| Weekend multiplier | F-072 (untested) |
| Neural dead-end | F-049/F-064 (worse than baseline) |

### Out-of-scope

- Горизонт > 1 год (Monte Carlo simulation, не прямое предсказание)
- Boardings per stop (только per route, F-020)
- Real-time streaming (только batch каждые 24 часа)

---

## Область адаптации (transfer scope)

### Как перенести на новый маршрут

1. Получить исторические boardings за ≥2 месяца (parquet, `ml/transit_ai/data/real.py`)
2. Добавить в `data/external/stops_routes.json` новый route_id с координатами
3. Добавить в `data/real/*.parquet` historical boardings
4. `make train-xgboost` с новым train-периодом
5. `make evaluate` — если `wape_score < 0.7`, маршрут не подходит

### Как перенести на новый период

1. Обновить `data/external/weather_2025.csv` через `make pipeline-fetch` или скачать вручную
2. Обновить `data/external/holidays_ru_YYYY.json`
3. `make train-xgboost --train-end YYYY-MM-DD`
4. Проверить holdout на новых месяцах

### Как перенести на новый город (⚠️ не рекомендуется)

Минимум:
1. OSM bbox нового города → `data/external/spb_*` / `kazan_*`
2. Перекалибровать `per_route_log_bias` (F-052) на новых данных
3. Перекалибровать `weather_openmeteo` (новые lat/lon)
4. Перекалибровать `holidays` (локальный календарь)
5. Переобучить XGBoost

Ожидаемая деградация: -0.10..-0.20pp vs Москва.

### Как добавить новый feature

1. Добавить в `data/external/<new>_2025.csv`
2. Добавить `ml/transit_ai/data/<new>.py` с фичей
3. `INSERT INTO feature_toggles (name, description, enabled) VALUES ('use_<new>', '...', false);`
4. `make train-xgboost`
5. Проверить holdout

---

## Метрики применимости

### Acceptance criteria

- ✅ Local holdout `WAPE-score ≥ 0.70` (D-016)
- ✅ Platform `WAPE-score ≥ 0.70` (target жюри)
- ✅ Submission покрывает 14 640 строк (F-045)
- ✅ Drift local vs platform ≤ 0.20pp (F-040)
- ✅ Runtime ≤ 2 сек (R6 SLA)

### Текущие значения (2026-09-26)

- Local holdout: `0.8751`
- Platform: `0.83455` (F-083 NEW BEST)
- Drift: -0.04pp
- Runtime: < 200ms (T-160 k6 smoke)

---

## Cross-references

- `docs/EXTERNAL_SOURCES.md` (T-202)
- `ml/transit_ai/data/real.py` (T-143)
- `apps/backend/app/models/prediction.py` (T-194)
- `apps/backend/app/api/predictions_db.py` (T-195)
- `.clinerules/05-hackathon-rules.md` R2-R6
- F-020, F-040, F-045, F-051, F-060, F-083
- T-203 (этот ticket)
