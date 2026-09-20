---
id: T-024
phase: 2
title: ml transit_ai data base ABC DataSource contract
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
tags: [ml, data, contract]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-024: ml transit_ai data base ABC DataSource contract

## Context

Why this task exists.

## Acceptance Criteria

- [x] `ml/transit_ai/data/base.py` с `DataSource` ABC (`load_stops()`, `load_routes()`, `load_ridership()`)
- [x] `DateRange` dataclass с валидацией (start <= end)
- [x] `validate_schema()` helper для impl'ов
- [x] 5 unit тестов passed (test_datasource_contract.py)
- [x] `ruff check ml/` clean

## Technical Notes

- ABC потому что нужны default impl для валидации схемы (R5 real data only, см. clinerule 05).
- Stops, routes, ridership — три pandas DataFrame.
- `load_ridership(date_range: DateRange)` — может быть тяжёлым, lazy.

## Verification

```bash
uv run pytest ml/tests/test_datasource_contract.py -v
```
