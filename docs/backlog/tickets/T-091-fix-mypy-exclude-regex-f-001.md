---
id: T-091
phase: 0
title: Fix mypy exclude invalid regex pattern (F-001)
priority: P1
effort: 1
unit: hours
rice:
  R: 3
  I: 1.0
  C: 1.0
  score: 3.0
depends_on: []
blocks: [T-088, T-089]
tags: [tooling, mypy, techdebt]
status: done
created: 2026-09-22
updated: 2026-09-22
assignee: "cline"
---

# T-091: Fix mypy exclude invalid regex pattern (F-001)

## Context

Discovery: `uv run mypy apps/backend/app/` errors with
`The exclude **/__pycache__ is an invalid regular expression,
because: nothing to repeat at position 0`.
Original pattern was set in Phase 0 (T-004). Blocks CI mypy gate.

## Acceptance Criteria

- [x] `uv run mypy apps/backend/app/` runs without the "invalid regular expression" error
- [x] Replace `**/__pycache__` (invalid regex) with `__pycache__` (matches any path component named `__pycache__`) in `[tool.mypy] exclude`
- [x] ruff `extend-exclude` and coverage `omit` (which accept globs) left untouched
- [x] Document the fix in findings.jsonl via update — already captured as F-001

## Verification

```bash
$ uv run mypy apps/backend/app/
apps/backend/app/api/predictions.py:12: error: Skipping analyzing "transit_ai.models.base": module is installed, but missing library stubs or py.typed marker  [import-untyped]
... (real type errors, but no regex error)
```

The original `**/__pycache__` regex error is gone. Remaining errors are
legitimate type-check issues for `transit_ai.models.{base,baseline}` (which is
expected — backend doesn't have stubs for the ML package) and missing
`dict[str, str]` annotations (will be fixed when T-017 lands Pydantic schemas).

## Notes

- mypy 1.x interprets `exclude` as **regex**, not glob. `**` is invalid regex
  because `*` alone means "zero or more of previous char" with nothing to repeat.
- ruff `extend-exclude` and coverage `omit` accept globs — they were OK.
- Future-proofing: if more modules need exclusion, prefer anchor-free simple
  substrings or use `[[tool.mypy.overrides]]` with `files = [...]`.
