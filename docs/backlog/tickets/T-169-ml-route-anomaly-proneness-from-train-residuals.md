---
id: T-169
phase: 2
title: Anomaly-proneness per route — из остатков train.csv (std residuals по (weekday, hour))
priority: P2
effort: 2
unit: hours
rice:
  R: 6
  I: 1.5
  C: 0.7
  score: 3.15
depends_on: [T-156, T-168]
blocks: []
tags: [ml, feature-engineering, anomaly-detection, route-context, data-driven]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-169: Anomaly-proneness per route (из train residuals)

## Context

T-168 даёт **разметочные** POI-фичи (hardcoded: школы/стадионы рядом).
Это **прокси** для "на этом маршруте бывают события".

Но есть **объективный data-driven сигнал**: 9 месяцев train.csv.
Для каждого маршрута можно посчитать baseline (mean по (weekday, hour))
и посмотреть **std residuals** (насколько сильно факт отклоняется от нормы).

**Гипотеза:** маршруты через стадионы/парки/университеты **объективно** дают
большие std residuals даже БЕЗ знания POI — просто потому что в случайный
день там может быть матч/концерт/экзамен, а в обычный — нет. Это коррелирует
с наличием POI, но **не зависит от разметки**.

**Преимущество перед T-168:**
- Полностью data-driven (никакого ручного труда)
- Работает для **любого маршрута**, даже если POI не размечены
- Устойчиво к ошибкам координат
- Ловит маршруты, которые мы **не знаем** как event-venue, но они ими являются

**Дополнение к T-168:** `route_anomaly_proneness` ≠ "есть стадион" —
это "объективная изменчивость пассажиропотока за 9 месяцев".

## Acceptance Criteria

- [ ] `ml/transit_ai/data/anomaly_features.py` — модуль:
  - [ ] `compute_baseline(df: pd.DataFrame) -> pd.DataFrame` — mean+std per (route, weekday, hour)
  - [ ] `compute_residuals(df, baseline) -> pd.Series` — `(actual - baseline_mean) / baseline_std`
  - [ ] `route_anomaly_proneness() -> pd.DataFrame` — для всех 10 маршрутов:
    - `residual_std` (float) — среднее std residuals за период
    - `residual_skew` (float) — асимметрия (положительная = события лучше среднего)
    - `anomaly_score` = `residual_std * (1 + residual_skew)` (композитный)
    - `p95_max_ratio` (float) — `p95(actual) / median(baseline)` (хвост)
    - `n_spike_hours` (int) — число часов где actual > 3×baseline
- [ ] `ml/transit_ai/data/_user_routes_2025.json` (или новый `data/external/anomaly_stats.json`):
  - [ ] Содержит предвычисленные stats для каждого из 10 маршрутов
  - [ ] Заполняется при `make anomaly-features` (один раз на реальных данных)
- [ ] `ml/tests/test_anomaly_features.py` — RED тесты:
  - [ ] `test_compute_baseline_shape`: groupby → правильный index
  - [ ] `test_residuals_no_nan`: residual нет NaN при непустом df
  - [ ] `test_route_anomaly_proneness_shape`: DataFrame shape (10, 5)
  - [ ] `test_route_50_high_anomaly`: route 50 (центр, театры) должен иметь anomaly_score > route 25 (спальный)
- [ ] `ml/transit_ai/models/xgboost_route.py`:
  - [ ] `_ANOMALY_FEATURES` tuple с 5 именами
  - [ ] `FEATURE_NAMES` расширен: `*_ANOMALY_FEATURES` после `*_POI_FEATURES`
- [ ] Submission #9:
  - [ ] Цель: ≥0.9025 на holdout (T-168+T-169 суммарно)
  - [ ] Если лучше → коммит `feat(ml): anomaly-proneness features (T-169)`

## Technical Notes

**Алгоритм:**
```python
def route_anomaly_proneness() -> pd.DataFrame:
    # 1. Load train.csv (9 months of validations → route × hour counts)
    df = load_train_boardings()  # (route_id, date, hour, boardings)
    
    # 2. Baseline: median per (route, weekday, hour)
    df["weekday"] = df["date"].dt.weekday
    baseline = df.groupby(["route_id", "weekday", "hour"])["boardings"].agg(
        median="median", std="std", p95=lambda s: s.quantile(0.95)
    )
    
    # 3. Merge residuals
    df = df.merge(baseline, on=["route_id", "weekday", "hour"])
    df["residual"] = (df["boardings"] - df["median"]) / df["std"].replace(0, 1)
    
    # 4. Aggregate per route
    out = df.groupby("route_id").agg(
        residual_std=("residual", "std"),
        residual_skew=("residual", lambda s: s.skew()),
        p95_max_ratio=("boardings", lambda s: s.quantile(0.95) / max(s.median(), 1)),
        n_spike_hours=("residual", lambda s: int((s > 3).sum())),
    )
    out["anomaly_score"] = out["residual_std"] * (1 + out["residual_skew"].clip(lower=0))
    return out.reset_index()
```

**Связь с T-168:** T-168 ловит **POI как cause**, T-169 ловит **effects**
(объективную изменчивость). Вместе — model получает оба сигнала:
- "Университет рядом" (T-168) + "трафик объективно прыгает" (T-169)
- Если они согласуются — модель увереннее
- Если расходятся — аномально (например, POI разметили, а трафик стабильный — значит POI неактивен)

**Где использовать:**
- Submission #9 = T-168 + T-169 (target: ≥0.9025 на holdout)
- Если target достигнут → рассматриваем T-170 (комбинированный анализ + retention)

## Verification

```bash
# 1. RED
make ml-test TEST=tests/test_anomaly_features.py
# Expected: ModuleNotFoundError or 4 failures

# 2. GREEN: реализовать anomaly_features.py + посчитать stats
make anomaly-features  # → data/external/anomaly_stats.json

# 3. Тесты зелёные
make ml-test TEST=tests/test_anomaly_features.py

# 4. Интеграция в XGBoost
make train-xgboost
make predict

# 5. Holdout WAPE ≥ 0.9025 (или ≥ 0.9015 если T-168/T-169 по отдельности)

# 6. Commit
git add ml/transit_ai/data/anomaly_features.py \
        ml/tests/test_anomaly_features.py \
        data/external/anomaly_stats.json \
        ml/transit_ai/models/xgboost_route.py
git commit -m "feat(ml): anomaly-proneness from train residuals (T-169)"
```

## Out of Scope

- ❌ Time-series anomaly detection (STL, Isolation Forest) — слишком сложно для хакатона
- ❌ Event calendar (KudaGo API → T-164, отдельный тикет)
- ❌ Per-route residual MAE (overlap с evaluate.py)
- ❌ Spike prediction (это predict.py, не feature)

## Status

`ready` → `in-progress` → `done`
