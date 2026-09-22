---
id: T-021
phase: 1
title: apps/backend GET api v1 models list active
priority: P1
effort: 3
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.7
  score: 2.333
depends_on: []
blocks: []
tags: [backend, api, models]
status: done
created: 2026-09-20
updated: 2026-09-22
assignee: cline
---

# T-021: apps/backend GET api v1 models list active

## Context

UI/operator dashboard needs to show **all available ML models** (which
were trained, what are their metrics, which one is currently active).
The `/api/v1/models/active` endpoint already exists but only returns the
active artifact. We need a sibling endpoint that returns the full list.

Endpoint is read-only — activation continues to happen via
`make activate-model-id=...` (filesystem atomicity, no DB roundtrip).

## Acceptance Criteria

- [x] `apps/backend/app/api/models.py` defines `router` with `GET /api/v1/models`
- [x] Response shape: `{models: [...], active_model_id: str|null, count: int}`
- [x] Each item in `models` has: `model_id`, `kind`, `version`, `trained_at`,
      `git_commit`, `horizons`, `granularities`, `metrics`, `is_active`
- [x] `is_active` flag is true exactly for the model whose id equals `active_model_id`
- [x] `?active_only=true` query parameter filters the list to just the active model
- [x] Endpoint returns 200 + empty list when no artifacts on disk (no crash)
- [x] Invalid `meta.json` files are **skipped silently** (they don't break the listing)
- [x] `ArtifactLoader.list_all()` and `ArtifactLoader.get_active_id()` added
- [x] `app.main.create_app()` registers the new router
- [x] OpenAPI `docs/api/openapi.json` regenerated and contains `/api/v1/models`
- [x] Tests `apps/backend/tests/test_models_list.py`: 6 tests pass
      (list-all, active flag, metadata shape, active_only filter, empty dir, skip-invalid)
- [x] All existing tests still pass (28 backend + 32 ml = 60/60)
- [x] ruff check clean on new files; mypy clean on new files (pre-existing
      `jsonschema` stubs error in loader.py is not new)

## Technical Notes

### Loader extensions

```python
# apps/backend/app/forecast/loader.py
def get_active_id(self) -> str | None:
    """Return active model_id without loading the full artifact.
    None when active.json is missing or malformed."""

def list_all(self) -> list[ModelArtifact]:
    """Return all valid artifacts, sorted alphabetically.
    Invalid meta.json entries are skipped (logged as warnings would be nice
    but kept silent for MVP — the listing must remain useful)."""
```

### Endpoint contract

```python
GET /api/v1/models?active_only=false

200 {
  "models": [
    {
      "model_id": "baseline_v1",
      "kind": "baseline",
      "version": "v0.1.0",
      "trained_at": "2026-09-22T20:00:00+00:00",
      "git_commit": "6ac0b22",
      "horizons": ["day"],
      "granularities": ["hour"],
      "metrics": {"rmsle": 0.28},
      "is_active": true
    },
    ...
  ],
  "active_model_id": "baseline_v1",
  "count": 2
}
```

### Design choices

- **Free function `_artifact_to_dict`, not Pydantic** — MVP. When the schema
  stabilizes, promote to `app.schemas.models.ModelInfo` (TypedDict for now).
- **`get_active_id()` separate from `get_active()`** — the listing endpoint
  doesn't need full artifact reload, just the pointer. Cheap separation.
- **Silent skip on invalid meta** — operators must still see the rest of the
  artifacts when one is broken (e.g. mid-training). Future: log warnings via
  `logging.getLogger(__name__)`.

## Verification (executed)

```bash
$ uv run pytest apps/backend/tests/test_models_list.py -v
============================= test session starts ==============================
collected 6 items

apps/backend/tests/test_models_list.py::test_list_models_returns_all_artifacts PASSED
apps/backend/tests/test_models_list.py::test_list_models_marks_active_flag PASSED
apps/backend/tests/test_models_list.py::test_list_models_includes_metadata PASSED
apps/backend/tests/test_models_list.py::test_list_models_filter_active_only PASSED
apps/backend/tests/test_models_list.py::test_list_models_returns_empty_when_no_artifacts PASSED
apps/backend/tests/test_models_list.py::test_list_models_skips_invalid_meta PASSED
============================== 6 passed in 0.47s ==============================

$ uv run pytest apps/backend/tests/ ml/tests/ -q --no-cov
60 passed, 2 warnings in 9.70s   # 28 backend + 32 ml

$ uv run ruff check apps/backend/app/api/models.py apps/backend/app/forecast/loader.py apps/backend/app/main.py apps/backend/tests/test_models_list.py
All checks passed!

$ uv run mypy apps/backend/app/api/models.py apps/backend/app/main.py
Success: no issues found in 2 source files

$ uv run python -c "from app.main import create_app; app=create_app(); print(list(app.openapi()['paths'].keys()))"
['/api/v1/healthz', '/api/v1/version', '/api/v1/readyz',
 '/api/v1/predictions/stop/{stop_id}', '/api/v1/models/active', '/api/v1/models', '/']
```

## Side findings (separate tickets)

- **make api-gen broken** — references `apps/backend/scripts/export_openapi.py`
  and `apps/backend/scripts/check_openapi.py` that don't exist. I generated
  openapi.json manually this time. Candidate for ticket F-002 / T-NNN (RICE ~3).

