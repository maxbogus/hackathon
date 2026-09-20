---
id: T-027
phase: 2
title: ml transit_ai models baseline mean predictor
priority: P0
effort: 3
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.7
  score: 2.333
depends_on: []
blocks: []
tags: [ml, baseline]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-027: ml transit_ai models baseline mean predictor

## Context

Why this task exists.

## Acceptance Criteria

- [x] `ml/transit_ai/models/baseline.py` с `BaselineMean(Predictor)`
- [x] `ml/transit_ai/models/base.py` с `Predictor` ABC и `PredictionPoint` dataclass
- [x] `fit(ridership_df)` строит dict[(stop_id, weekday, hour)] -> (mean, std)
- [x] Global fallback по (weekday, hour) для cold-start (новых остановок)
- [x] `predict(stop_id, period_start, period_end)` → list of PredictionPoint (one per hour)
- [x] Lower/upper = max(0, mean ± std)
- [x] Save/load через pickle (dict-формат)
- [x] 7 unit тестов passed (test_baseline.py) — fit, predict, unknown_stop, save/load roundtrip, RMSLE < 1.2, edge cases
- [x] `ruff check ml/transit_ai/models/` clean
- [x] E2E: predictions endpoint возвращает данные из baseline_v1 артефакта

## Technical Notes

- "Mean of (weekday, hour) for this stop". Если stop новый — глобальный fallback.
- Predictor ABC в `ml/transit_ai/models/base.py` (создаётся в этом тикете).
- `extract_period(start, end)` делит на hourly slots, sum внутри.

## Verification

```bash
uv run pytest ml/tests/test_baseline.py -v
# 4+ теста: fit returns dict, predict matches mean, save→load roundtrip, RMSLE threshold
```
