---
id: T-126
phase: 1
title: retrain XGBoost на реальных данных с exogenous фичами + измерение импакта
priority: P1
effort: 2
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.7
  score: 3.5
depends_on: [T-125]
blocks: []
tags: [ml, retrain, exogenous, evaluation]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-126: retrain XGBoost на реальных данных с exogenous фичами + измерение импакта

## Context

После T-125 (exogenous features) — нужно
**переобучить модель** на полном наборе фичей и **доказать жюри**, что exogenous features
улучшают метрики. Без измерения импакта — это «маркетинговое заявление», с измерением —
«доказательство».

## Acceptance Criteria

- [ ] Pipeline:
  1. Загрузить реальные данные через `RealSource` (когда данные появятся от оргкомитета)
  2. Добавить weather через T-123
  3. Добавить traffic через T-124
  4. Добавить lag features (стандартный фичеинжиниринг в `ml/transit_ai/data/features.py`)
  5. Обучить XGBoost v3 с полным набором фичей
  6. Сохранить в `ml/artifacts/xgboost_v3/`
- [ ] Сравнительная таблица метрик (baseline → v1 → v2 → v3):
  - `xgboost_v1`: только временные фичи (hour, weekday)
  - `xgboost_v2`: + lag features
  - `xgboost_v3`: + exogenous (weather, traffic)
- [ ] Метрики: RMSLE, MAE, MAPE на holdout
- [ ] Если v3 лучше v2 — задокументировать дельту (% улучшения)
- [ ] Если v3 хуже или нет данных — обосновать (например, "exogenous данные за период неполные")
- [ ] Markdown отчёт: `docs/reports/xgboost_exogenous_impact.md`
- [ ] Коммит с Conventional Commits: `feat(ml): retrain XGBoost v3 with exogenous features (T-126)`

## Technical Notes

```python
# ml/scripts/retrain_xgboost_v3.py
from transit_ai.data.weather import fetch_historical_weather
from transit_ai.data.traffic import fetch_osm_traffic_features
from transit_ai.data.features import add_exogenous_features
from transit_ai.models.xgboost_pred import XGBoostPredictor
from transit_ai.training.registry import ModelRegistry

# 1. Load real data
real_df = load_real_ridership()

# 2. Fetch weather (cached)
weather_df = fetch_historical_weather(55.75, 37.62, "2024-01-01", "2026-09-23")

# 3. Fetch traffic (cached)
traffic_df = fetch_osm_traffic_features((55.55, 37.30, 55.92, 37.85))

# 4. Merge
df = add_exogenous_features(real_df, weather_df, traffic_df)

# 5. Train
predictor = XGBoostPredictor(model_id="xgboost_v3")
predictor.fit(df)
registry = ModelRegistry()
registry.save(predictor, ...)
```

## Verification

```bash
make train-xgboost-v3  # новый target

# Метрики в meta.json
cat ml/artifacts/xgboost_v3/meta.json | jq .metrics

# Сравнительная таблица
cat docs/reports/xgboost_exogenous_impact.md
```

## Beneficiary Impact

**Город (⭐⭐⭐⭐)** — измеримое улучшение точности модели.
**Департамент (⭐⭐⭐⭐)** — доказательство, что подход работает (а не «trust me, ML is great»).

RICE: 3.5 — средний. Делается в Фазе 1.
