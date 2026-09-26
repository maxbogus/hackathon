# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-26T21:27:22Z
# Обновлено: Cline (агент) — T-NEW-A: make install → uv sync --all-packages. Долг T-NEW ликвидирован.

## Что сделано в этой сессии

**1. Реальные баги (исправлены):**
- ✅ `apps/mcp/tests/test_tools.py` — collection error из корня (root conftest.py добавлен)
- ✅ `apps/backend/tests/test_config.py::test_settings_loads_with_defaults` — хрупкий к `TRANSIT_AI_DATABASE_URL=sqlite` в env (добавлен `monkeypatch.delenv`)
- ✅ `apps/frontend/src/lib/i18n/t.test.ts` — snapshot mismatch (`analyst` ключ добавлен)

**2. Negative/corner case покрытие (добавлены тесты):**
- `ml/tests/test_submission_manifest.py`: 7 тестов (missing_csv, malformed_json, expected_rows mismatch, dataset_hash empty, dataset_hash distinct, git_commit, git_branch)
- `ml/tests/test_validators_lookup.py`: 4 теста (train missing → FileNotFoundError, weekday=99, weekday=-1, corrupted cache)
- `apps/backend/app/api/predictions_db.py`: добавлена валидация (`from_date < to_date`, `coef ∈ [0,3]`) в `export_predictions_csv`

**3. CI infrastructure:**
- `Makefile` `test` target переписан для per-app pytest (избегаем `tests` package shadow)
- `test-pipeline` и `test-root` как отдельные таргеты (для harvester/sandbox/ml_pipeline и root tests/)
- `pyproject.toml` `testpaths` убран корневой `tests/` (выделено в `test-root`)
- `.venv/bin/python` использован напрямую вместо `python3` (избегаем PATH race)

## Результат

**`make test`:** ✅ 615 тестов passed (123 backend + 387 ml + 13 assistant + 9 mcp + 83 vitest)
**`make test-root`:** ✅ 135 тестов passed (clinerules, load SLA, dockerfile)
**`make test-pipeline`:** ✅ 22 теста passed (7 harvester + 12 sandbox + 3 ml_pipeline)

**ИТОГО: 772 теста, все зелёные.**

## Известные долги

- ✅ **RESOLVED:** `uv sync --all-packages --extra dev` — теперь в Makefile `install`. Чистая установка с нуля даёт все deps (fastapi, sqlalchemy, celery, pydantic, openpyxl, aiosqlite, ...).
- `ml/transit_ai/data/poi_features.py` (60% coverage) и `ml/transit_ai/benchmark/{cli,compare,report}.py` (0-36%) всё ещё имеют пробелы в negative cases.

## Что сделано в следующей мини-сессии

**T-NEW-A:** `make install` теперь использует `uv sync --all-packages --extra dev` вместо `uv sync --extra dev`. Это workspace-correct way — устанавливает все workspace members (`apps/backend`, `apps/assistant`, `apps/mcp`, `apps/harvester`, `apps/ml_pipeline`, `apps/sandbox`, `ml`) одной командой. Verified с чистым `rm -rf .venv && make install` → все deps доступны, `make test` 615 passed.

