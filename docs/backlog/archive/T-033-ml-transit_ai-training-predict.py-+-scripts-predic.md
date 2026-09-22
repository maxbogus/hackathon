---
id: T-033
phase: 2
title: ml transit_ai training predict.py + scripts predict.py parquet
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
tags: [ml, predict]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: ""
---

# T-033: ml transit_ai training predict.py + scripts predict.py parquet

## Context

Why this task exists.

## Acceptance Criteria

- [ ] `make predict` пишет `predictions/<date>_<model_id>.parquet` с колонками: `period_start, period_end, stop_id, route_id, value, lower, upper, horizon, granularity, model_id, scenario_id?` — соответствует `docs/schemas/predictions.schema.json`
- [ ] Default: `horizon=day`, `granularity=hour`, `from=now`, `to=now+24h`, `model_id=active.json`
- [ ] `--horizon=day|month|year` переключает временной диапазон (24h / 30d / 12m) и гранулярность (hour / day / month)
- [ ] `--model-id=<id>` переопределяет active.json (для backtest: `--model-id=baseline_v1`)
- [ ] `--from <ISO>` / `--to <ISO>` — гибкое окно предсказания
- [ ] `ml/transit_ai/training/predict.py` экспортирует `predict(stop_ids, from_dt, to_dt, model_id, horizon) -> pl.DataFrame` — переиспользуется из `scripts/predict.py` и в будущем из backend forecast (T-042 контракт)
- [ ] Если `calibration.json` существует в артефакте — применяется к predictions (интеграция с T-034)
- [ ] Parquet schema соответствует контракту: используем `pyarrow` (или `polars.write_parquet`)
- [ ] Юнит-тест: `ml/tests/test_predict.py::test_predict_writes_parquet_with_correct_schema` — файл существует, колонки + dtypes правильные, n_points > 0
- [ ] `make check-all` зелёный

## Technical Notes

- Входные данные: для predict **не нужны** исторические данные — Predictor уже fitted. ModelRegistry.load() восстанавливает state, потом .predict(stop_id, from, to) → list[PredictionPoint]
- Для backtest (evaluation) — избегаем look-ahead: predict только на будущее относительно training cutoff
- `predictions.schema.json` определён в `docs/schemas/predictions.schema.json` — validate через jsonschema после записи
- Stop IDs: берём из `data/synthetic/stops.parquet` или (когда появится RealSource) из `data/real/stops.parquet` — fallback на все 800 из Synthetic

## Verification

```bash
make ...
```
