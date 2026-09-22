---
id: T-039
phase: 2
title: ml scripts benchmark_baseline.py + benchmark_all.py
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
tags: [ml, benchmark, scripts]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: ""
---

# T-039: ml scripts benchmark_baseline.py + benchmark_all.py

## Context

Why this task exists.

## Acceptance Criteria

- [ ] `make benchmark-baseline` завершается за <60 сек на synthetic (Strategy=grid, max_configs=1, folds=2), пишет `docs/reports/benchmark_baseline_smoke.md`
- [ ] `make benchmark-all` (defaults: strategy=grid, max_configs=12, folds=4) запускает ≥4 конфигов из PRESET_CONFIGS
- [ ] `make benchmark-all --strategy=random --max-configs=10` работает и пишет `docs/reports/benchmark_<date>.md`
- [ ] Каждый `BenchmarkResult` содержит обязательные поля `git_commit`, `seed`, `train_data_hash` (R6 hackathon-rules, reproducibility)
- [ ] CLI использует `transit_ai.data.synthetic.SyntheticSource` (не hardcoded `_synthetic_data()`) — данные реалистичнее для grid search
- [ ] Юнит-тест: `ml/tests/test_benchmark_scripts.py` — оба скрипта запускаются без exception + результат валиден по JSON Schema
- [ ] `make check-all` зелёный (ruff + mypy strict + pytest)

## Technical Notes

- Сейчас `cli.py::_synthetic_data()` использует hardcoded daily seasonality → переключить на `SyntheticSource(SyntheticConfig(n_days=35, seed=42)).load_ridership(DateRange(...))`
- Aggregation: для benchmark нужна одна колонка `value` + `date` (как ожидает `runner.walk_forward_splits`). Для SyntheticSource → нужно агрегировать ridership по `(date, stop_id)` → sum или mean
- Train data hash: sha256 от parquet-serialized SyntheticSource output (`hash_dataframe` уже есть в `training/registry.py`)
- `scripts/benchmark_baseline.py` уже существует → дополнить только если criterion не покрыт

## Verification

```bash
make ...
```
