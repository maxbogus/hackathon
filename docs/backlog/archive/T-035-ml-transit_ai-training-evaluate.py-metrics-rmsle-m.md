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
status: done
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

- [x] `ml/transit_ai/reports/metrics.py` содержит `rmsle/mae/mape/compute_metrics` (DRY: импортируется из benchmark/runner.py, локальные дубликаты удалены)
- [x] `ml/transit_ai/training/registry.py` имеет `ModelRegistry.load(model_id) -> Predictor` с диспетчером по `meta["kind"]` (baseline → BaselineMean.load, xgboost → XGBoostPredictor.load, остальные → NotImplementedError)
- [x] `ml/transit_ai/training/evaluate.py` экспортирует `evaluate_artifact(model_id, ridership_df, ...) -> EvaluationResult` (in-memory predict на holdout, не зависит от T-033 predict.py)
- [x] `ml/transit_ai/training/evaluate.py` обновляет `meta.json.metrics` через registry (git_commit/trained_at/seed сохраняются)
- [x] `ml/scripts/evaluate.py` CLI: дефолт = active model из `active.json`, опции `--model-id`, `--holdout-days`
- [x] `docs/reports/evaluate_<model_id>_<YYYY-MM-DD>.md` создаётся с таблицей метрик
- [x] `make evaluate` exit=0, печатает RMSLE/MAE/MAPE в stdout
- [x] `uv run pytest ml/tests/ tests/ apps/backend/tests/ -q --no-cov` → 81/81 зелёные
- [x] `uv run ruff check` на моих файлах → clean (pre-existing BLE001/DTZ011 в benchmark/cli.py и benchmark_all.py — не моих рук дело)
- [x] `uv run mypy ml/transit_ai/reports/ ml/transit_ai/training/evaluate.py ml/scripts/evaluate.py` → clean
- [x] Conventional Commit (`feat(ml): evaluate.py with RMSLE/MAE/MAPE metrics (T-035)`) + push в origin (`db30e53`) + archive + handoff-update

## Technical Notes

**In-memory подход (не parquet):** T-035 работает на `predictor.predict(stop_id, ts, ts+1h)`
в цикле по holdout-рядам. Это позволяет сделать T-035 независимо от T-033 (predict.py → parquet),
согласуется с `depends_on: []` в тикете. T-033 будет читать этот же контракт predictor'а
для генерации parquet.

**Holdout split:** последние `holdout_days=7` дней `ridership_df` (или явный `[holdout_start, holdout_end)`).
Каждая строка holdout = (stop_id, timestamp, passenger_count) → 1 PredictionPoint → 1 значение для сравнения.

**Диспетчер по `kind`:** минимальный для baseline + xgboost (уже реализованы).
GRU/Hybrid/Monte Carlo → NotImplementedError с понятным сообщением "tracker: T-029/T-030".

**Synthetic tz-naive issue:** SyntheticSource внутри сравнивает timestamps через `pd.Timestamp.normalize()`,
что падает на tz-aware datetime. Workaround: `# noqa: DTZ001` в scripts/evaluate.py (строки с `datetime(2026, 1, 1)`).
T-026 (RealSource) может потребовать правки.

**Report формат** (`docs/reports/evaluate_<model>_<date>.md`):
```markdown
# Evaluation Report — baseline_v1
Generated: 2026-09-22T19:20:44Z
Git commit: 0d58869
Holdout: 2026-01-29..2026-02-04 (1488 stops)
Eval time: 0.48s

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| RMSLE | 0.6953 | ≤ 0.5 | ❌ |
| MAE | 29.5187 | ≤ 15.0 | ❌ |
| MAPE | 102.2259 | ≤ 25.0 | ❌ |
```

## Verification

```bash
# Tests (81 total)
uv run pytest ml/tests/ tests/ apps/backend/tests/ -q --no-cov

# Lint + types (мои файлы)
uv run ruff check ml/transit_ai/reports/ ml/transit_ai/training/evaluate.py \
                    ml/transit_ai/training/registry.py ml/transit_ai/benchmark/runner.py \
                    ml/scripts/evaluate.py ml/tests/test_metrics.py ml/tests/test_evaluate.py
uv run mypy ml/transit_ai/reports/ ml/transit_ai/training/evaluate.py ml/scripts/evaluate.py

# Live eval (active model = baseline_v1)
make evaluate

# Verify meta.json обновился
cat ml/artifacts/baseline_v1/meta.json | python3 -m json.tool | grep -A 4 metrics

# Verify report создан
cat docs/reports/evaluate_baseline_v1_2026-02-04.md
```

## Verification Logs (commit db30e53)

```
✅ 81/81 tests passed (60 baseline + 21 new: 7 test_metrics + 8 test_evaluate + 6 dispatcher)
✅ Ruff clean на моих файлах (4 pre-existing ошибки в benchmark/{cli.py,benchmark_all.py} — не трогал)
✅ Mypy clean на моих файлах (2 pre-existing в registry.py — jsonschema stubs + unused type:ignore)
✅ make evaluate exit 0:
     RMSLE  = 0.6953
     MAE    = 29.52
     MAPE % = 102.23
     n_points = 1488
✅ meta.json: metrics заполнен, git_commit (0d58869) + seed (42) + trained_at сохранены
✅ docs/reports/evaluate_baseline_v1_2026-02-04.md создан
✅ Benchmark smoke (make benchmark-baseline) — без regression (RMSLE 0.2841 как раньше)
✅ D-006 в ledger: метрики перенесены в reports/metrics.py
✅ Commit db30e53 pushed to origin (70a02eb..db30e53)
```
