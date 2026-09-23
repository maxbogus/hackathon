# 21-runtime-uv.md — uv как единый package manager для всего Python-стека

## Hard Rule (R21 в hackathon-rules)

**Весь Python-код проекта — локально, в Docker, в ML-скриптах —
запускается через [uv](https://github.com/astral-sh/uv) версии 0.5.7+.**

Никакого прямого `python`, `pip`, `pip-tools` или `poetry`.
Фронтенд (`apps/frontend/`) — через **yarn 4 corepack**, это другой стек, см. `06-tooling.md`.

## Почему uv

1. **Lockfile-aware**: `uv.lock` коммитится, воспроизводимые сборки (R3 hackathon-rules).
2. **Workspaces**: один `uv sync` обновляет все пакеты (`apps/backend`, `apps/assistant`, `apps/mcp`, `ml/`).
3. **Быстро**: на 10-100× быстрее `pip` за счёт Rust-имплементации и параллельного resolver.
4. **Совместимо с Docker**: `uv==0.5.7` пинится в `Dockerfile`, даёт тот же lockfile.
5. **Не зависит от ОС**: на macOS, Linux, WSL — одинаковое поведение.

## Где uv используется

| Контекст | Команда | Где |
|---|---|---|
| Локальная установка всех deps | `uv sync --extra dev` | `Makefile` → `install` |
| Локальный запуск Python | `uv run python script.py` | `Makefile` → все цели с скриптами |
| ML скрипты (вне Docker) | `uv --directory ml run python scripts/<x>.py` | `Makefile` → `train-*`, `predict`, `calibrate` |
| Backend в Docker | `uv run --package transit-ai-backend uvicorn app.main:app` | `apps/backend/Dockerfile` CMD |
| Backend Dockerfile deps install | `uv sync --frozen --no-dev --package transit-ai-backend` | `apps/backend/Dockerfile` RUN |
| MCP server | `cd apps/mcp && uv run python server.py` | `Makefile` → `mcp-run` |
| Assistant smoke | `cd apps/assistant && uv run python -c "..."` | `Makefile` → `assistant-test` |
| Tests | `uv run pytest apps/...` | `Makefile` → `test` |
| Lint + format | `uv run ruff check/format` | `Makefile` → `lint`, `format` |
| Typecheck | `uv run mypy apps/...` | `Makefile` → `typecheck` |

## Где uv НЕ используется

- ❌ **Frontend** (`apps/frontend/`): yarn 4 corepack. См. `06-tooling.md`.
- ❌ **postgres/redis**: стандартные Docker images (`timescale/timescaledb`, `redis:7-alpine`).
- ❌ **Node tooling** (eslint, prettier, vitest): через yarn workspace.

## Правила для скриптов вне Docker

Все Python-скрипты в проекте запускаются через Makefile → `uv run`:

```bash
# Правильно: через Makefile
make train-baseline
make predict
make ledger-add

# Неправильно: напрямую
python scripts/train_baseline.py
python3 ml/scripts/predict.py
pip install ...
```

Каждый скрипт проекта (кроме `apps/frontend/**`) должен быть подключён через
target в `Makefile`. Если скрипт ещё не подключён — добавить WIP-маркер в `Makefile`,
а не вызывать напрямую.

## WIP-маркеры в Makefile

Цели в `Makefile` на ещё-не-реализованные скрипты помечаются `[WIP: T-NNN]` и
выводят `@echo "WIP: pending T-NNN. Skipped."`. Это:
- делает состояние явным в `make help`
- не ломает другие цели (`make help`, `make train-all`)
- даёт понятный трекинг на тикеты

Пример:

```makefile
# WIP (T-027): XGBoost trainer not yet implemented
train-xgboost: ## Train XGBoost  [WIP: T-027]
	@echo "WIP: pending T-027 (XGBoost trainer). Skipped."
```

После реализации скрипта — заменить `@echo` на реальный `$(UV) --directory ml run python scripts/train_xgboost.py`.

## Dockerfile backend: uv обязательно

```dockerfile
# apps/backend/Dockerfile (зафиксировано)
FROM python:3.12-slim AS runtime
RUN pip install --no-cache-dir uv==0.5.7
WORKDIR /app
COPY pyproject.toml uv.lock* ./
COPY apps/backend/pyproject.toml ./apps/backend/
RUN uv sync --frozen --no-dev --package transit-ai-backend 2>/dev/null \
 || uv sync --no-dev --package transit-ai-backend
COPY apps/backend ./apps/backend
CMD ["uv", "run", "--package", "transit-ai-backend", \
     "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**Почему `uv sync` в Docker, а не `pip install -r requirements.txt`:**
- `requirements.txt` устарел бы при каждом изменении deps (нужно его генерить отдельно).
- `uv sync` читает `pyproject.toml` + `uv.lock` напрямую — один источник правды.
- `--frozen` гарантирует reproducible build (R3 hackathon-rules).

## Не делать

- ❌ `pip install <package>` напрямую (даже в Docker — `pip` нужен только для установки `uv` один раз)
- ❌ `python script.py` без `uv run` (мимо virtualenv)
- ❌ `poetry install` / `poetry run` (uv заменяет poetry)
- ❌ `conda install` (uv не интегрируется с conda env)
- ❌ Создавать `requirements.txt` рядом с `pyproject.toml` (drift)
- ❌ Менять версию `uv` в Dockerfile без ADR (зафиксировано `uv==0.5.7`)
- ❌ Запускать Python-скрипты в обход `Makefile` (нарушает audit trail)

## Что делать при добавлении нового Python-скрипта

1. **Создать файл** в `scripts/`, `ml/scripts/`, `apps/backend/scripts/`, `apps/assistant/scripts/`, или `apps/mcp/`.
2. **Добавить target в Makefile** с префиксом WIP, если скрипт пока stub:
   ```makefile
   # WIP (T-NNN): описание
   my-new-target: ## Описание  [WIP: T-NNN]
   	@echo "WIP: pending T-NNN. Skipped."
   ```
3. **После реализации** — заменить `@echo` на `$(UV) [run|--directory] python <path>`.
4. **Добавить target в `.PHONY`** (одной строкой, в начало Makefile).
5. **Префикс команды в help**: `make help` автоматически подхватит.

## Skills

Длинная инструкция по `uv` для агентов — `ai/skills/01-uv-package-manager.md`
(команды, workspaces, troubleshooting, миграция с pip).
