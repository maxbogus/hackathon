# 06-tooling.md — Toolchain

## Python: uv + ruff + mypy + pytest

### uv (>= 0.5.7)

```bash
# Установка
curl -LsSf https://astral.sh/uv/install.sh | sh

# Workspace (apps/*, ml)
uv sync --extra dev

# Запуск без активации venv
uv run python script.py
uv run pytest tests/
uv run ruff check .
uv run mypy app/
```

`uv.lock` коммитим. `pyproject.toml` — source of truth.

### ruff (>= 0.5.7) — lint + format

```bash
# Проверка
uv run ruff check apps/ ml/ scripts/

# Автофикс
uv run ruff check --fix apps/ ml/ scripts/

# Формат
uv run ruff format apps/ ml/ scripts/
```

Полный набор правил в корневом `pyproject.toml` (`[tool.ruff.lint]`).

### mypy (>= 1.10.1) — strict types

```bash
uv run mypy apps/backend/app apps/assistant/app apps/mcp/
```

Strict mode + warn_unused_ignores + no_implicit_optional.
ML библиотеки в overrides (torch, xgboost, etc.).

### pytest (>= 8.3.0) — unit + integration

```bash
# Unit (без Docker)
uv run pytest apps/ ml/ -m unit -q --no-cov

# Integration (требует `make up`)
uv run pytest apps/backend/tests -m integration -v --no-cov

# Coverage
uv run pytest --cov=apps --cov=ml --cov-report=html
```

Маркеры: `unit`, `integration`, `slow`, `gpu`.

## Node: yarn 4 (corepack) + vite + vitest + tsc + eslint

### yarn 4 через corepack

```bash
# Активация (один раз)
corepack enable

# В package.json указано: "packageManager": "yarn@4.5.0"
yarn install                    # НЕ npm install, НЕ pnpm install

# Workspace команды
yarn workspace @transit-ai/frontend add react-leaflet
yarn workspace @transit-ai/frontend remove leaflet
```

### vite (>= 5.4.0)

```bash
cd apps/frontend
yarn dev                        # dev server :5173
yarn build                      # production build (с tsc --noEmit)
yarn preview                    # serve dist/
```

### vitest (>= 2.0.5)

```bash
cd apps/frontend
yarn test                       # watch mode
yarn test:run                   # run once (CI)
yarn test:cov                   # coverage
```

### tsc (>= 5.5.4) — strict TypeScript

```bash
cd apps/frontend
yarn typecheck                  # tsc --noEmit
```

`strict: true` + `noUncheckedIndexedAccess` + `noImplicitOverride` + `noImplicitReturns`.

### eslint (>= 9.10.0) — flat config

```bash
cd apps/frontend
yarn lint                       # eslint + prettier --check
yarn format                     # autofix
```

ESLint flat config (`eslint.config.js`), без `.eslintrc`.

### prettier (>= 3.3.3)

Конфиг в `.prettierrc.json`. Исключения: `apps/frontend/src/generated/`.

## Docker compose

```bash
make up        # docker compose up -d
make down      # docker compose down
make logs      # docker compose logs -f
```

Конфиг в `docker-compose.yml` (root).

## Orval (генерация TS из OpenAPI)

```bash
# Генерация
make fe-gen    # = cd apps/frontend && yarn orval --config orval.config.ts

# Вход: docs/api/openapi.json (генерится backend)
# Выход: apps/frontend/src/generated/
```

**НИКОГДА** не редактировать файлы в `generated/` вручную.

## CI (когда добавим)

GitHub Actions: lint + typecheck + test + api-check + ledger-check.

## Версии

Зафиксированы в `pyproject.toml` и `package.json`. Проверяются через `make check-all`.
