---
id: T-042
phase: 3
title: apps/backend GET api v1 predictions stop id route id (MVP)
priority: P0
effort: 4
unit: hours
rice:
  R: 8
  I: 3.0
  C: 0.7
  score: 4.2
depends_on: [T-019, T-020, T-027, T-031]
blocks: []
tags: [backend, ml, predictions, mvp]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-042: Predictions endpoint (MVP — baseline only)

## Context

First end-to-end working slice: backend reads active artifact, calls BaselineMean.predict(),
returns hourly predictions JSON. Critical-path для MVP demo.

## Acceptance Criteria

- [x] `GET /api/v1/predictions/stop/{stop_id}?period_start=...&period_end=...` → 200 with `{stop_id, model_id, horizon, granularity, data: [...]}`
- [x] `GET /api/v1/models/active` → 200 with artifact metadata
- [x] Validation: period_start < period_end (else 400)
- [x] 503 with clear error if no active artifact
- [x] 501 if active model kind != "baseline" (XGBoost/GRU/Hybrid plug in later)
- [x] 4 unit tests (test_predictions.py) using dependency_overrides for test isolation
- [x] E2E verified via curl: real artifact from registry → real predictions returned

## Verification (executed)

```bash
$ curl http://localhost:8765/api/v1/models/active
{"model_id":"baseline_v1","kind":"baseline","version":"v0.1.0",...}

$ curl 'http://localhost:8765/api/v1/predictions/stop/1?period_start=2026-02-01T07:00:00&period_end=2026-02-01T10:00:00'
{"stop_id":1,"model_id":"baseline_v1","horizon":"day","granularity":"hour","data":[
  {"period_start":"2026-02-01T07:00:00","period_end":"2026-02-01T08:00:00","value":21.33,"lower":19.25,"upper":23.41},
  ...
]}
```

## Notes

- Currently only `kind="baseline"` supported — predictor dispatcher uses isinstance check.
- XGBoost/GRU plug in via the same `_get_predictor()` dispatcher in T-028..T-030.
- Dependency injection: `app.dependency_overrides[predictions.get_loader] = lambda: test_loader` in tests.
- All errors mapped to HTTPException with clear detail messages.
