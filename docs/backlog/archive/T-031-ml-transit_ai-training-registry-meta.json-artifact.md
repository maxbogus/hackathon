---
id: T-031
phase: 2
title: ml transit_ai training registry meta.json artifact contract
priority: P0
effort: 4
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.7
  score: 2.625
depends_on: []
blocks: []
tags: [ml, contract, registry]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-031: ml transit_ai training registry meta.json artifact contract

## Context

Why this task exists.

## Acceptance Criteria

- [x] `ml/transit_ai/training/registry.py` с `ModelRegistry`
- [x] `save(predictor, version, ...)` пишет `meta.json` (валидируется против schema) + `model.pkl`
- [x] `activate(model_id)` пишет `active.json` с atomic pointer
- [x] `git_commit()` и `hash_dataframe()` хелперы для reproducibility (R3 hackathon-rules)
- [x] Rejects unfitted predictors (RuntimeError → ValueError)
- [x] 8 unit тестов passed (test_registry.py) — meta.json, schema validation, activate, save→load roundtrip, error cases
