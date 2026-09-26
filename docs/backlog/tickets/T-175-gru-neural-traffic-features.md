---
id: T-175
phase: 2
title: Traffic features (T-124) + GRU нейронка (T-029) + ablation analysis
priority: P1
effort: 6
unit: hours
rice:
  R: 9
  I: 2.5
  C: 0.7
  score: 3.50
depends_on: [T-174]
blocks: []
tags: [ml, traffic, gru, neural, features, ablation, drift]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-175: Traffic (T-124) + GRU (T-029) + ablation analysis

## Context

После T-174 feature flags готовы. Теперь:
1. Traffic (пробки) features (T-124) - 3 фичи на основе OSM каталога
2. GRU нейронка (T-029) - sequence model для route × hour (по образцу contest)
3. Ablation analysis - понять вклад каждой feature group

Local holdout 0.9047 -> platform 0.18-0.35 (F-040). Непредсказуемый drift.
Нужно проверить: какие фичи реально помогают (vs добавляют шум)?

## Acceptance Criteria

- [x] T-124 done: traffic_osm.py + 40 точек в JSON + 16 тестов
- [x] Feature flags поддерживают use_traffic
- [ ] T-029 done: GRURoutePredictor (по образцу contest experiment_neural_gru.py)
- [ ] Ablation script: для каждого варианта (no_events/no_poi/no_external/base_only/full/with_traffic) train + holdout eval
- [ ] Ablation report в docs/reports/ablation_2026-09-26.md
- [ ] F-049 в ledger (feature importance выводы)
- [ ] D-030 в ledger (GRU architecture decision)

## Verification

```bash
make test
uv run --directory ml python scripts/ablation.py --output docs/reports/ablation_2026-09-26.csv
uv run --directory ml python scripts/make_submission.py   --flags-file ml/transit_ai/config/variants/with_traffic.yaml   --model-id xgboost_v11_traffic --submission-id v11-traffic
```

## Status

`ready` -> `in-progress` -> `done` (после ablation analysis)
