---
id: T-035
phase: 2
title: ml transit_ai training evaluate.py metrics RMSLE MAE MAPE
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
tags: [ml, metrics]
status: in-progress
created: 2026-09-20
updated: 2026-09-22
assignee: "maxbogus"
---

# T-035: ml transit_ai training evaluate.py metrics RMSLE MAE MAPE

## Context

Production-eval pipeline: load fitted artifact → predict on ridership holdout → compute
RMSLE/MAE/MAPE → write report → update `meta.json.metrics`. Closes existing broken
`make evaluate` target (Makefile:117) and populates empty `metrics: {}` in baseline_v1/xgboost_v1.

Metrics (`rmsle/mae/mape`) currently live in `ml/transit_ai/benchmark/runner.py` and are
duplicated across tests — refactor target: move to shared `ml/transit_ai/reports/metrics.py`
(пакет `reports/` уже создан и пуст с правильным docstring "Метрики (RMSLE, MAE, MAPE)
и графики").

## Acceptance Criteria

- [ ] `ml/transit_ai/reports/metrics.py` содержит `rmsle/mae/mape/compute_metrics` (DRY: импортируется из benchmark/runner.py, локальные дубликаты удалены)
- [ ] `ml/transit_ai/training/registry.py` имеет `ModelRegistry.load(model_id) -> Predictor` с диспетчером по `meta["kind"]` (baseline → BaselineMean.load, xgboost → XGBoostPredictor.load, остальные → NotImplementedError)
- [ ] `ml/transit_ai/training/evaluate.py` экспортирует `evaluate_artifact(model_id, ridership_df, ...) -> EvaluationResult` (in-memory predict на holdout, не зависит от T-033 predict.py)
- [ ] `ml/transit_ai/training/evaluate.py` обновляет `meta.json.metrics` через registry (git_commit/trained_at/seed сохраняются)
- [ ] `ml/scripts/evaluate.py` CLI: дефолт = active model из `active.json`, опции `--model-id`, `--holdout-days`
- [ ] `docs/reports/evaluate_<model_id>_<YYYY-MM-DD>.md` создаётся с таблицей метрик
- [ ] `make evaluate` exit=0, печатает RMSLE/MAE/MAPE в stdout
- [ ] `uv run pytest ml/tests/ -q --no-cov` → все зелёные (60 baseline + ~9 новых)
- [ ] `uv run ruff check ml/transit_ai/reports/ ml/transit_ai/training/ ml/scripts/ ml/tests/` → clean
- [ ] `uv run mypy ml/transit_ai/ ml/scripts/` → clean
- [ ] Conventional Commit + push в origin + archive + handoff-update

## Technical Notes

**In-memory подход (не parquet):** T-035 работает на `predictor.predict(stop_id, ts, ts+1h)`
в цикле по holdout-рядам. Это позволяет сделать T-035 независимо от T-033 (predict.py → parquet),
согласуется с `depends_on: []` в тикете. T-033 будет читать этот же контракт predictor'а
для генерации parquet.

**Holdout split:** последние `holdout_days=7` дней `ridership_df` (или явный `[holdout_start, holdout_end)`).
Каждая строка holdout = (stop_id, timestamp, passenger_count) → 1 PredictionPoint → 1 значение для сравнения.

**Диспетчер по `kind`:** минимальный для baseline + xgboost (уже реализованы).
GRU/Hybrid/Monte Carlo → NotImplementedError с понятным сообщением "tracker: T-029/T-030".

**Report формат** (`docs/reports/evaluate_<model>_<date>.md`):
```markdown
# Evaluation Report — baseline_v1
Generated: 2026-09-22T20:30:00Z
Git commit: 70a02eb
Holdout: 2026-01-22..2026-01-28 (7 days, N stops)

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| RMSLE  | 0.42  | ≤ 0.5     | ✅     |
| MAE    | 12.3  | ≤ 15      | ✅     |
| MAPE % | 18.5  | ≤ 25      | ✅     |
```

## Verification

```bash
# Tests
uv run pytest ml/tests/test_metrics.py ml/tests/test_evaluate.py -v --no-cov

# Lint + types
uv run ruff check ml/transit_ai/reports/ ml/transit_ai/training/ ml/scripts/ ml/tests/
uv run mypy ml/transit_ai/ ml/scripts/

# Run evaluate (active model = baseline_v1)
make evaluate

# Verify meta.json обновился
cat ml/artifacts/baseline_v1/meta.json | grep -A 5 metrics

# Verify report создан
ls -la docs/reports/evaluate_*.md
```
