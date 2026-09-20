---
id: T-019
phase: 1
title: apps/backend forecast module stub + loader interface
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
tags: [backend, ml, contract]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-019: apps/backend forecast module stub + loader interface

## Context

Why this task exists.

## Acceptance Criteria

- [x] Создан `apps/backend/app/forecast/loader.py` с классом `ArtifactLoader`
- [x] `ArtifactLoader.load(model_id: str) -> ModelArtifact` валидирует `meta.json` против `docs/schemas/prediction_artifact.schema.json`
- [x] `ArtifactLoader.get_active() -> ModelArtifact` читает `ml/artifacts/active.json` и возвращает активный артефакт
- [x] Падает с `ArtifactValidationError` (обёртка над jsonschema) если артефакт невалиден
- [x] Падает с `ArtifactNotFoundError` если `meta.json` отсутствует
- [x] FastAPI dependency `get_loader()` через singleton
- [x] 6/6 unit тестов passed (apps/backend/tests/test_loader.py)
- [x] `ruff check` clean
- [x] `mypy --strict` clean (с `types-jsonschema` в dev deps)

## Technical Notes (выполнено)

- Реализован с делением exceptions на `ArtifactError` → `ArtifactNotFoundError`, `ArtifactValidationError`, `ActiveArtifactNotFoundError`
- `ModelArtifact` — frozen dataclass с slots
- `ArtifactLoader.schema` — lazy property с кэшированием
- `get_loader()` — singleton (сбрасывается через `reset_loader_cache()` в тестах)
- `DEFAULT_ARTIFACTS_DIR = REPO_ROOT/ml/artifacts` (через `Path(__file__).parents[4]`)

## Technical Notes

- Контракт: `docs/schemas/prediction_artifact.schema.json` (создаётся в Этапе 1)
- Artifacts dir: `ml/artifacts/<model_id>/{meta.json, model.pkl, preprocessor.pkl}`
- Active symlink: `ml/artifacts/active.json` → `{"model_id": "baseline_v1"}`
- DI: `get_loader()` через FastAPI `Depends`
- ModelArtifact — Protocol с методами `predict(stop_id, horizon, granularity) -> dict`

## Verification

```bash
uv run pytest apps/backend/tests/test_loader.py -v
# должно быть ≥ 4 теста passed
```
