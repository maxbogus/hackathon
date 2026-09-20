---
id: T-020
phase: 1
title: apps/backend GET api v1 healthz version readyz
priority: P1
effort: 2
unit: hours
rice:
  R: 5
  I: 1.0
  C: 0.7
  score: 1.75
depends_on: []
blocks: []
tags: [backend, health]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-020: apps/backend GET api v1 healthz version readyz

## Context

Why this task exists.

## Acceptance Criteria

- [x] `GET /api/v1/healthz` → 200 `{"status": "ok"}` (без внешних зависимостей)
- [x] `GET /api/v1/version` → 200 `{"version": "0.1.0", "git_commit": "e3d7abb"}`
- [x] `GET /api/v1/readyz` → 200 со структурой `{"status": "ok", "checks": {...}}`
- [x] OpenAPI генерится на `/openapi.json` + Swagger UI на `/docs`
- [x] Тесты используют `TestClient(app)` (без docker) — 4/4 passed
- [x] Роутер подключён в `main.py` через `app.include_router(health_router)`

## Notes

- Реальные проверки DB (T-016) и Redis (T-018) в `/readyz` отложены — сейчас placeholder.
- `git_commit` через `subprocess` (best-effort, не падает если не git repo).

## Technical Notes

- Router: `apps/backend/app/api/health.py` с `APIRouter(prefix="/api/v1")`
- `version` читается из `app.__version__` (зафиксирован в `app/__init__.py`)
- `git_commit` через `subprocess.check_output(["git", "rev-parse", "HEAD"])` (только для debug)
- readyz: try/except на подключение к postgres и redis (через `Depends(get_db)` + redis ping)

## Verification

```bash
uv run pytest apps/backend/tests/test_health.py -v
curl http://localhost:8000/api/v1/healthz  # {"status":"ok"}
```
