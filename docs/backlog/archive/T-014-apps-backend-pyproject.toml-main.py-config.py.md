---
id: T-014
phase: 1
title: apps/backend pyproject.toml main.py config.py
priority: P0
effort: 4
unit: hours
rice:
  R: 3
  I: 2.0
  C: 0.7
  score: 1.05
depends_on: []
blocks: []
tags: [backend, skeleton]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-014: apps/backend pyproject.toml main.py config.py

## Context

Why this task exists.

## Acceptance Criteria

- [x] `apps/backend/app/main.py` создаёт FastAPI app и подключает роутеры
- [x] `apps/backend/app/config.py` с `Settings(BaseSettings)` читает `.env` (database_url, redis_url, app_env)
- [x] `apps/backend/app/__init__.py` экспортирует `__version__ = "0.1.0"`
- [x] CORS middleware настроен (для frontend на :5173)
- [x] `uv run uvicorn app.main:app --reload` запускается и отвечает
- [x] 7 unit тестов в apps/backend/tests/test_main.py passed
- [x] 5 unit тестов в apps/backend/tests/test_config.py passed
- [x] `ruff check apps/backend/` clean

## Verification (выполнено)

```bash
$ curl http://localhost:8765/api/v1/healthz
{"status":"ok"}
$ curl http://localhost:8765/api/v1/version
{"version":"0.1.0","git_commit":"e3d7abb","app_env":"dev"}
$ uv run pytest apps/backend/ -q
18 passed
```

## Notes

- pyproject.toml backend уже создан в фазе 0 (Docker stub) — этот тикет только заполнил код.
- mypy strict не запускался: pre-existing баг `**/__pycache__` regex в `[tool.mypy].exclude` (F-001). Отдельный тикет T-091.
- types-jsonschema добавлен в `[project.optional-dependencies].dev` apps/backend/pyproject.toml.

## Technical Notes

- `Settings` через `pydantic-settings`: `DatabaseURL`, `RedisURL`, `AppEnv: Literal["dev","prod"]`, `CorsOrigins: list[str]`
- main.py использует `lifespan` контекст для startup/shutdown
- Тесты: `TestClient` из FastAPI, monkeypatch `Settings` через env vars
- TDD: тест config первый → потом main.py

## Verification

```bash
uv run pytest apps/backend/tests/test_config.py apps/backend/tests/test_main.py -v
uv run uvicorn app.main:app --reload
# должно подняться на http://localhost:8000
```
