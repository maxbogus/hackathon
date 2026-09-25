---
id: T-152
phase: 2
title: XGBoost retrain с per-route + lag/rolling фичами для WAPE uplift
priority: P0
effort: 3
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.7
  score: 3.5
depends_on: [T-148, T-149]
blocks: []
tags: [ml, xgboost, per-route, lag-features, hackathon, wape, retrain]
status: in-progress
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-152: XGBoost retrain с per-route + lag/rolling фичами

## Context

После T-148 (calendar features не помогли, F-022) и T-146b EDA (`docs/reports/eda_data.md`):

1. **9 routes с разными паттернами**: route 17 mean=2069 vs route 25 mean=323 (6.4× разрыв)
2. **Weekend ratio per route**: route 50=0.45 (спальный), route 25=0.74 (равномерный)
3. **Drift train→test**: +10-22% осенью относительно лета
4. **CV внутри bucket (route,hour)**: 0.18 дневные vs 2.12 ночные

RouteBaselineMean (текущая модель, holdout WAPE=0.8751) — bucket averaging,
не может выучить route-specific interactions. XGBoost с маршрутом как категорией
+ lag фичами может дать +2-5pp WAPE на платформе.

## Что делаем

### 1. Адаптировать XGBoostPredictor

Текущий `ml/transit_ai/models/xgboost_pred.py` (260 строк) требует:
- колонку `passenger_count` (не `boardings` как в labels)
- колонку `stop_id` (нет в route-level labels)
- только quantile objective

Изменения:
- Переименовать target `passenger_count` → `boardings`
- Сделать `stop_id` опциональным (default = None, пропускается в фичах)
- Добавить новые фичи в FEATURE_NAMES:
  - `is_holiday` (из T-148 calendar_rf)
  - `lag_24h`, `lag_168h`, `lag_730h` (hour/day/month lag)
  - `rolling_mean_24h`, `rolling_mean_168h`, `rolling_mean_30d`
- Сохранить `reg:squarederror` objective (проще чем quantile) +
  отдельно predict для CI через квантильную регрессию q=0.1, 0.9
- Включить `route_id` как категориальную фичу (XGBoost нативно поддерживает через enable_categorical=True)

### 2. ml/scripts/train_xgboost.py

```python
"""Train XGBoost on hackathon real data (T-152).

Args:
    --start-date, --end-date: train period
    --model-id: e.g. xgboost_v2
    --n-estimators, --max-depth, --learning-rate: hyperparams
    --submission-id: для манифеста
"""
```

Шаги:
1. Load train (янв-авг 2025)
2. Compute lag/rolling features на полном train + concat с test для корректных lag
3. Train XGBoost (3 quantile boosters for CI)
4. Evaluate on holdout (сен-окт 2025) → holdout WAPE
5. Save model + meta.json в ml/artifacts/<model_id>/
6. **Print SUBMISSION CANDIDATE block** (через skill 04)

### 3. ml/scripts/predict_xgboost.py (или reuse make_submission.py)

Расширить `make_submission.py`:
- `--model-kind {route_baseline, xgboost}` для выбора predictor
- Для xgboost: загрузить артефакт из ml/artifacts/<model_id>/model.pkl
- Predict с lag/rolling features (для submission периода ноя-дек lag нужно вычислять
  на обучающих данных, доступных на момент прогноза — это известная проблема
  forecasting. Решение: использовать **forecasted lag from same model** recursive,
  или **mean of last N weeks** для холодного старта)

### 4. Тесты

`ml/tests/test_xgboost_real.py`:
- `test_xgboost_fit_on_real_data` (на labels_day_train.csv)
- `test_xgboost_holdout_wape_better_than_baseline` (WAPE xgboost < WAPE baseline)
- `test_xgboost_predict_batch_returns_correct_shape`
- `test_xgboost_save_load_roundtrip_real`
- `test_xgboost_features_include_lag_rolling`

### 5. Makefile target

Заменить `[WIP: T-027]` на реальный target:
```makefile
train-xgboost: ## Train XGBoost with lag/rolling features (T-152)
$(UV) run --directory ml python scripts/train_xgboost.py     --start-date 2025-01-01 --end-date 2025-08-31     --model-id xgboost_v2 --submission-id v5-xgboost
```

## Acceptance Criteria

- [ ] XGBoostPredictor.fit() принимает boardings (не passenger_count)
- [ ] XGBoostPredictor работает БЕЗ stop_id (только route-level)
- [ ] Новые фичи в FEATURE_NAMES: is_holiday, lag_24h, lag_168h, lag_730h, rolling_*
- [ ] ml/scripts/train_xgboost.py готов и подключён через Makefile
- [ ] `make train-xgboost` запускается, holdout WAPE < 0.8751 (RouteBaselineMean)
- [ ] Submission v5-xgboost сгенерирован (14640 строк + manifest)
- [ ] SUBMISSION CANDIDATE блок выводится после make_submission.py
- [ ] Все тесты passed (ml/tests/test_xgboost*.py)
- [ ] ruff check + format clean

## Verification

```bash
make train-xgboost
# Holdout WAPE должен быть < 0.8751 (текущий baseline)
# Ожидаем 0.78-0.82

make submission MODEL_ID=xgboost_v2 SUBMISSION_ID=v5-xgboost
# Должен вывести SUBMISSION CANDIDATE block

uv run pytest ml/tests/test_xgboost_real.py -v --no-cov
ruff check ml/transit_ai/models/xgboost_pred.py ml/scripts/train_xgboost.py
```

## Risks

- **Lag features на ноя-дек**: для submission (ноя-дек 2025) lag_24h = boardings за
  сутки до прогноза — нет данных (test period заканчивается 31.10). Решение:
  recursive prediction (predict t→use as lag for t+1) ИЛИ использовать только
  rolling mean без lag.
- **Overfitting**: route_id как категория + 46K train rows + много фичей может
  переобучиться. Защита: ранняя остановка (early_stopping_rounds=20) на holdout.
- **Долгое обучение**: 3 quantile boosters × 200 trees ≈ 1-2 мин на CPU.

## Cross-references

- F-020: per-route diagnose
- F-022: T-148 не помог (negative result)
- F-023: платформа WAPE=0.73231 (bias-corrected)
- docs/reports/eda_data.md: полный EDA
- T-148: calendar features (negative result, но is_holiday пригодится здесь)
- T-148a: clinerule 23 manifest
- T-149: SUBMISSION CANDIDATE block (правило и skill)

## Не делаем

- ❌ GRU/Hybrid (T-029, T-031) — слишком долго, рискованно
- ❌ Weather (T-123) — отложено в post-hackathon
- ❌ Events feature (Timepad/Яндекс.Афиша) — R4 + низкий импакт на ноя-дек
