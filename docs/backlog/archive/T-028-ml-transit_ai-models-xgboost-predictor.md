---
id: T-028
phase: 2
title: ml transit_ai models xgboost predictor
priority: P1
effort: 4
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.7
  score: 2.625
depends_on: []
blocks: []
tags: [ml, xgboost]
status: done
created: 2026-09-20
updated: 2026-09-22
assignee: "cline"
---

# T-028: ml transit_ai models xgboost predictor

## Context

XGBoost — первая «настоящая» ML модель после baseline. Используем tabular
features (hour, weekday, stop_id, route_id, lat, lon, sin/cos time encodings).
RMSLE на синтетике должен быть лучше baseline (~0.28 → ~0.20).

Это таблица для дифференциации в презентации: «baseline даёт X, наш
ML-pipeline даёт Y».

## Acceptance Criteria

- [x] `ml/transit_ai/models/xgboost_pred.py` реализует `XGBoostPredictor(Predictor)`
- [x] Поддерживает `device="cuda"` если доступно, fallback на `"cpu"` (через torch.cuda.is_available())
- [x] Feature engineering: hour, weekday, is_weekend, hour_sin/cos, stop_id, route_id, month, day_of_year (lat/lon отложены — требуют join со stops, отдельный тикет)
- [x] `fit(ridership)` строит 3 quantile boosters (q=0.1/0.5/0.9) по log1p(passenger_count)
- [x] `predict(...)` возвращает non-negative `value` с CI через quantile regression
- [x] `save(path)` / `load(path)` через joblib + native XGBoost JSON (boosters не pickle-friendly)
- [x] Тесты `ml/tests/test_xgboost.py`: 7 тестов проходят (fit, predict, save/load, empty, unknown stop, finite, beats baseline)
- [x] mypy strict: clean
- [x] ruff check + format: clean

## Technical Notes

### Зависимости

- xgboost >= 2.1 (добавлено в T-023)
- Для device="cuda" нужен CUDA toolkit; на машинах без GPU — fallback на cpu.

### Feature engineering

```python
def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    df["hour"] = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month"] = df["timestamp"].dt.month
    df["day_of_year"] = df["timestamp"].dt.dayofyear
    return df
```

Категориальные (stop_id, route_id) обрабатываем через label encoding.

### CI (confidence interval)

Используем quantile regression: `objective="reg:quantileerror"` с `quantile_alpha=[0.1, 0.5, 0.9]`.
Один fit даёт три модели: q10 (lower), q50 (value), q90 (upper).

### Сохранение

XGBoost Booster НЕ pickle-friendly. Используем joblib или native
`model.save_model()`. Через Predictor.save/load — единый интерфейс.

## Verification (executed)

```bash
$ uv run --package transit-ai-ml pytest ml/tests/test_xgboost.py -v
============================= test session starts ==============================
collected 7 items

ml/tests/test_xgboost.py::test_xgboost_can_fit PASSED
ml/tests/test_xgboost.py::test_xgboost_predict_returns_one_point_per_hour PASSED
ml/tests/test_xgboost.py::test_xgboost_predict_for_unknown_stop PASSED
ml/tests/test_xgboost.py::test_xgboost_save_load_roundtrip PASSED
ml/tests/test_xgboost.py::test_xgboost_handles_empty_ridership PASSED
ml/tests/test_xgboost.py::test_xgboost_finite_values PASSED
ml/tests/test_xgboost.py::test_xgboost_beats_baseline_on_synthetic PASSED
============================== 7 passed in 8.60s ===============================

$ uv run mypy ml/transit_ai/models/xgboost_pred.py
Success: no issues found in 1 source file

$ uv run ruff check ml/transit_ai/models/xgboost_pred.py ml/tests/test_xgboost.py
All checks passed!

$ uv run pytest ml/tests/ -q
32 passed in 6.53s   # все ml тесты (включая existing baseline)
```
