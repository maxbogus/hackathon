---
id: T-034
phase: 2
title: ml transit_ai training calibrate.py bucket biases
priority: P1
effort: 4
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.7
  score: 1.75
depends_on: []
blocks: []
tags: [ml, calibration]
status: ready
created: 2026-09-20
updated: 2026-09-20
assignee: ""
---

# T-034: ml transit_ai training calibrate.py bucket biases

## Context

Why this task exists.

## Acceptance Criteria

- [ ] `make calibrate` создаёт `ml/artifacts/<active>/calibration.json` со структурой `{kind: "bucket" | "segmental" | "shrink", edges, biases, alpha, n_obs}`
- [ ] Default bucket strategy: `(stop_id, weekday, hour)` — для каждой комбинации bias = mean(actual - pred) на holdout
- [ ] Shrinkage: `bias_effective = α·bias_bucket + (1-α)·bias_global`, где `α = n_bucket / (n_bucket + prior)` (prior = 100)
- [ ] Калибровка применяется к `predictions/*.parquet` — adjustment = exp(bias_effective) в log-space (count data)
- [ ] После калибровки RMSLE на holdout **уменьшается** vs uncalibrated (sanity check, логируется)
- [ ] `calibration.json` валиден против `prediction_artifact.schema.json.calibration` (jsonschema.validate)
- [ ] `--strategy bucket|segmental|shrink` — переключение алгоритма
- [ ] Юнит-тест: `ml/tests/test_calibrate.py::test_calibrate_updates_predictions_and_metadata` — после calibrate.json существует, RMSLE уменьшился
- [ ] Контракт с `transit_ai.training.predict`: при наличии `calibration.json` — predictions корректируются на лету
- [ ] `make check-all` зелёный

## Technical Notes

- **Reference implementation**: адаптация `~/Repositories/contest/ecup26-user-value/scripts/apply_bucket_calibration.py` (см. D-005 в ledger)
- Bucket aggregation: `df.groupby(['stop_id', 'weekday', 'hour']).agg({'residual': 'mean', 'n': 'size'})`
- Per-bucket effective bias с shrinkage: `bias = (sum_residual + prior * global_bias) / (n + prior)`
- Калибровка в log-space: `value_calibrated = exp(log(value) + bias)` (соответствует D-005 — гибридная модель в log-space)
- Файл `calibration.json` обновляется через `registry.update_metrics()` ИЛИ новый метод `registry.update_calibration(model_id, calib_dict)` (предпочтительно — выделить отдельный метод)

## Verification

```bash
make ...
```
