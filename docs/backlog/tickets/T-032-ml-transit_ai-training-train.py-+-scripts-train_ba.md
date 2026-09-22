---
id: T-032
phase: 2
title: ml transit_ai training train.py + scripts train_baseline.py
priority: P0
effort: 5
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.7
  score: 2.1
depends_on: []
blocks: []
tags: [ml, training]
status: ready
created: 2026-09-20
updated: 2026-09-20
assignee: ""
---

# T-032: ml transit_ai training train.py + scripts train_baseline.py

## Context

Why this task exists.

## Acceptance Criteria

- [ ] `make train-baseline` создаёт `ml/artifacts/baseline_v1/model.pkl` + `meta.json` + обновляет `active.json` → `{"model_id": "baseline_v1"}`
- [ ] `ml/artifacts/baseline_v1/meta.json` валиден против `docs/schemas/prediction_artifact.schema.json` (jsonschema.validate)
- [ ] `meta.json.train_data_hash` = sha256 от synthetic ridership DataFrame (через `registry.hash_dataframe`)
- [ ] `ml/transit_ai/training/train.py` экспортирует общую функцию `train_model(model_cls, config) -> SaveResult` (используется и для baseline, и для xgboost/gru/hybrid в будущем)
- [ ] Гиперпараметры читаются из `ml/configs/baseline.yaml` (через `make train-baseline MACHINE=rtx5060` — тоже работает)
- [ ] `--seed 42` принимается из CLI → попадает в `meta.json.seed` и в Predictor.fit (reproducibility R6)
- [ ] Юнит-тест: `ml/tests/test_train_baseline.py::test_train_baseline_creates_artifact_and_activates` — после запуска скрипта артефакт + active.json существуют и валидны
- [ ] `make train-xgboost` тоже работает через тот же `train_model(model_cls, ...)` (доказывает переиспользуемость)
- [ ] `make check-all` зелёный (ruff + mypy strict + pytest)

## Technical Notes

- Универсальная `train_model(model_cls, config: TrainConfig)` обёртка — принимает `model_cls` (Predictor подкласс), `config` с полями `n_days, seed, model_id, horizon, granularity, hyperparams`
- Конфиг через `ml/configs/base.yaml` (общие) + `ml/configs/baseline.yaml` (специфика BaselineMean, например window=7d для fit)
- SyntheticSource → fit(model) → registry.save(...) → registry.activate(model_id)
- Совместимость с `train_xgboost.py` (T-038+ скрипты, когда появятся): тот же `train_model(XGBoostPredictor, cfg)`

## Verification

```bash
make ...
```
