---
id: T-173
phase: 2
title: CatBoostRoutePredictor + rank-average blend с xgboost_v9_events (T-172)
priority: P1
effort: 3
unit: hours
rice:
  R: 7
  I: 2.0
  C: 0.7
  score: 3.27
depends_on: [T-152, T-172]
blocks: []
tags: [ml, blend, catboost, ensemble, rank-average]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-173: CatBoost-route + rank-average blend с XGBoost

## Context

T-152 сделал XGBoost v9_events — лучший raw model (wape_score=0.9051).
Но per-route bias calibration в submission pipeline стирает разницу с v8_poi (оба 0.8751).

Из литературы 2026 года (Zhou et al., Ma et al.) — **ансамблирование** tabular
моделей даёт +1.5–5pp на стационарных holdout. Подход Zhang & Qu (Beijing metro):
**stacking RF + XGBoost + CatBoost + SVR + KNN** через meta-learner.

Наш хакатон — route-only данные с lag/rolling фичами, без SVR/KNN (медленно для
14640 строк). Реалистичный baseline: **rank-average blend** XGBoost + CatBoost
(по образцу `~/Repositories/evehicle_pred/scripts/blend.py`, проверено в проде).

## Decision

**2 новых компонента:**

1. **`ml/transit_ai/models/catboost_route.py`** — `CatBoostRoutePredictor` с тем
   же интерфейсом, что и `XGBoostRoutePredictor`:
   - `fit(ridership)` — обучает один CatBoostRegressor (median, без quantile CI для скорости)
   - `predict_batch(df, lag_lookup)` — median predictions
   - Использует **тот же** `_make_features` через импорт (все 35 фичей включая events T-172)
   - Гиперпараметры: `iterations=300, depth=6, learning_rate=0.05, loss_function='RMSE'`

2. **`ml/scripts/blend.py`** — rank-average blend:
   - Загружает 2 артефакта (XGBoost + CatBoost) из `ml/artifacts/`
   - `predict_batch` на holdout → `scipy.stats.rankdata` каждой модели → усреднение → нормировка → масштабирование к среднему boardings
   - Сохраняет в `predictions/submission_blend_<ts>.csv` через `make_submission.py --model-kind blend`

**Submission model_id = `blend_xg_cat_v1`** — будет использовать в manifest.

## Acceptance Criteria

- [ ] `ml/transit_ai/models/catboost_route.py` — CatBoostRoutePredictor класс
- [ ] `ml/scripts/train_catboost.py` — entry point (по образцу train_xgboost.py)
- [ ] `ml/scripts/blend.py` — rank-average blender (по образцу evehicle_pred)
- [ ] `ml/transit_ai/models/xgboost_route.py` — FEATURE_NAMES вынесен в общий модуль ИЛИ импортируется в catboost_route
- [ ] `ml/tests/test_catboost_route.py` — минимум 3 теста:
      [ ] `test_catboost_fit_predict` — fit на маленьком df → predict shape правильный
      [ ] `test_catboost_uses_same_features_as_xgboost` — feature_names совпадают с XGBoostRoutePredictor
      [ ] `test_catboost_predict_with_lag_lookup` — inference без boardings + lag_lookup → preds >= 0
- [ ] `ml/tests/test_blend.py` — минимум 3 теста:
      [ ] `test_rank_average_shape` — выход (n_rows,) длина совпадает с входами
      [ ] `test_rank_average_monotone` — если XGB const higher → blend выше
      [ ] `test_rank_average_bounds` — все значения в [0, max(XGB, Cat)]
- [ ] `make check-all` зелёный
- [ ] `train_catboost.py --model-id catboost_v1` отрабатывает
- [ ] `blend.py` создаёт submission с manifest.json
- [ ] Если holdout WAPE-score > 0.8751 — залить на платформу
- [ ] Если ≤ 0.8751 — НЕ заливать, F-NNN в ledger
- [ ] F-047 в ledger (platform score для v9-events), F-048 (blend result)

## Technical Notes

**Source files:**
- `ml/transit_ai/models/catboost_route.py` — новый (~150 строк, по образцу xgboost_route)
- `ml/scripts/train_catboost.py` — новый (~120 строк, по образцу train_xgboost.py)
- `ml/scripts/blend.py` — новый (~100 строк)
- `ml/tests/test_catboost_route.py`, `ml/tests/test_blend.py` — новые

**Shared features:** можно либо (а) вынести `_make_features` в `ml/transit_ai/models/_features.py`,
либо (б) просто импортировать `from transit_ai.models.xgboost_route import _make_features, FEATURE_NAMES`.
Вариант (б) проще и не ломает существующие импорты.

**Submission pipeline integration:** `make_submission.py --model-kind blend`
требует расширения choices в argparse. Реализация — в `ml/scripts/blend.py`,
не в make_submission.py (избегаем риска сломать существующий pipeline).

## Verification

```bash
make test
uv run --directory ml python scripts/train_catboost.py \
  --start-date 2025-01-01 --end-date 2025-08-31 \
  --holdout-start 2025-09-01 --holdout-end 2025-10-31 \
  --model-id catboost_v1
uv run --directory ml python scripts/blend.py \
  --models xgboost_v9_events catboost_v1 \
  --submission-id v10-blend
# → SUBMISSION CANDIDATE block, manifest.json
```

## Status

`ready` → `in-progress` → `done`
