# Skill: uv package manager (01-uv-package-manager)

> Длинная инструкция для AI-агентов по использованию uv в проекте Transit-AI.
> Загружается по требованию через `use_skill("01-uv-package-manager")`.
> Короткая версия правил — в `.clinerules/21-runtime-uv.md`.

## Назначение

uv (Astral) — единый package manager для всего Python в проекте: backend, ML,
assistant, MCP, скрипты. Версия **0.5.7** зафиксирована в `apps/backend/Dockerfile`.

Когда этот скилл нужен: при работе с `pyproject.toml`, `uv.lock`, скриптами,
Dockerfile backend, ML trainer/predictor, workspace-структурой.

## Структура проекта (uv workspaces)

```
hackathon/
├── pyproject.toml          # root: [tool.uv.workspace] members = ["apps/*", "ml"]
├── uv.lock                  # единственный lockfile (коммитится)
├── apps/
│   ├── backend/pyproject.toml   # transit-ai-backend
│   ├── assistant/pyproject.toml # transit-ai-assistant
│   └── mcp/pyproject.toml       # transit-ai-mcp
└── ml/
    └── pyproject.toml      # transit-ai-ml
```

Члены workspace: все `apps/*` и `ml/`. `scripts/` — это root-level утилиты,
не отдельный workspace member.

## Установка и обновление

```bash
# Установить uv (один раз на машину)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Проверить версию (должна быть 0.5.7+)
uv --version

# Синхронизировать все workspace members + dev extras
uv sync --extra dev

# Только prod deps (используется в Docker)
uv sync --no-dev --package transit-ai-backend

# С frozen lockfile (в Docker для reproducibility)
uv sync --frozen --no-dev --package transit-ai-backend
```

## Запуск Python-кода

```bash
# Из корня репо
uv run python scripts/ledger.py add
uv run pytest apps/backend/tests -m unit

# Из конкретного workspace member
uv --directory ml run python scripts/train_baseline.py
uv --directory apps/assistant run python -c "from app.providers.registry import REGISTRY; print(REGISTRY.keys())"

# С явным указанием пакета (редко нужно)
uv run --package transit-ai-ml python -m transit_ai.training.train

# Через Makefile (ПРЕДПОЧТИТЕЛЬНО — единая точка входа)
make train-baseline
make ledger-add
make test
```

## Добавление зависимости

```bash
# В root pyproject.toml (общая для всех)
uv add polars

# В конкретный workspace member
uv add --package transit-ai-backend sqlalchemy

# В dev extras
uv add --extra dev pytest-asyncio

# Из конкретного индекса (Torch CUDA wheels)
uv add torch --index pytorch-cu121

# Обновить lockfile
uv lock

# Обновить конкретный пакет
uv lock --upgrade-package polars
```

## Lockfile (`uv.lock`)

- ✅ Коммитим в git (R3 hackathon-rules: reproducible).
- ❌ НЕ читать в контекст LLM (он большой — см. MEMORY-BUDGET.md).
- Используется Docker через `uv sync --frozen`.

## Workspaces и зависимости между ними

```toml
# apps/backend/pyproject.toml
[project]
name = "transit-ai-backend"
dependencies = [
    "transit-ai-ml",          # workspace dep (не из PyPI)
    "fastapi>=0.115",
    "sqlalchemy>=2.0",
]

[tool.uv.sources]
transit-ai-ml = { workspace = true }    # ссылка на ../ml
```

`uv sync` резолвит workspace-члены автоматически.

## Docker backend (apps/backend/Dockerfile)

```dockerfile
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

Ключевые моменты:
- `uv==0.5.7` пинится явно (защита от breaking changes).
- `pip install` используется **один раз** — для установки самого `uv`.
- `uv sync --frozen` — гарантирует что `uv.lock` не меняется в Docker-сборке.
- CMD запускает uvicorn через `uv run --package` (не напрямую через python).

## Troubleshooting

### `uv sync` падает с "Lock file not found"
```bash
# Сгенерировать lockfile
uv lock
```

### "Module not found" при `uv run`
```bash
# Сначала sync
uv sync --extra dev

# Если не помогло — пересоздать venv
rm -rf .venv && uv sync --extra dev
```

### Конфликт версий при добавлении пакета
```bash
# Показать текущий резолв
uv lock --dry-run

# Принудительно обновить проблемный пакет
uv add --upgrade-package <name>

# Если совсем плохо — пересоздать lockfile
rm uv.lock && uv lock
```

### В Docker не работает `uv run`
```bash
# Проверить что uv установлен
docker exec backend which uv

# Проверить что pyproject.toml доступен
docker exec backend ls -la /app/pyproject.toml

# Запустить shell и посмотреть
docker exec -it backend uv run python -c "import sys; print(sys.path)"
```

### "Workspaces are not supported in this version"
```bash
# Проверить uv версию
uv --version   # должна быть 0.5.7+

# Workspace support появился в 0.4.7+, обновить если < 0.5.7
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Миграция с pip (если встретишь legacy код)

```bash
# Было (legacy):
pip install -r requirements.txt
python manage.py runserver

# Стало (uv):
uv sync --extra dev
make dev   # или uv run python manage.py runserver
```

## Best practices

1. **Не редактируй `uv.lock` вручную** — используй `uv add` / `uv lock`.
2. **Не дублируй deps** — если пакет нужен и backend, и ML — добавь в root `pyproject.toml`.
3. **Используй workspace deps** для cross-package импортов (`transit-ai-ml = { workspace = true }`).
4. **Пини версии в Dockerfile** — `RUN pip install --no-cache-dir uv==0.5.7`.
5. **Все скрипты — через Makefile** — не запускай `python script.py` напрямую.
6. **Перед коммитом** — `uv lock --check` (если pyproject.toml менялся).

## Что НЕ делать

- ❌ `pip install <pkg>` напрямую в Docker (используй `uv add` и пересобери).
- ❌ `python script.py` (мимо venv → ModuleNotFoundError).
- ❌ `poetry install/run` (uv заменяет poetry).
- ❌ `requirements.txt` рядом с `pyproject.toml` (drift).
- ❌ Удалять `uv.lock` без причины (потеря reproducibility).

## Связанные документы

- `.clinerules/21-runtime-uv.md` — hard rule и обзор
- `.clinerules/06-tooling.md` — общий tooling (ruff, mypy, vite, vitest, tsc, eslint, orval)
- `.clinerules/10-ml-as-scripts.md` — почему ML вне Docker
- `apps/backend/Dockerfile` — референс правильного Dockerfile
- `Makefile` — единая точка входа для всех скриптов
- `MEMORY-BUDGET.md` — не читать `uv.lock` в контекст
