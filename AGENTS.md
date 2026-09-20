# AGENTS.md — Hackathon: Прогноз загрузки трамваев Москвы

> Универсальные правила для AI-агентов (Cline, Claude Code, Aider, …) на этом проекте.
> Только Cline протестирован. Cline-специфичные правила — в [`.clinerules/`](.clinerules/).

---

## Project Overview

**Transit-AI** — интерактивный веб-сервис прогнозирования пассажиропотока трамваев Москвы.
Прогнозы на 3 горизонта (день/месяц/год), привязка к геопозиции (остановки/маршруты/округа),
ML-модели обучаются скриптами (вне Docker), API читает артефакты по контрактам,
фронт получает данные через Orval-сгенерированные хуки.

| Атрибут | Значение |
|---|---|
| Домен | Городской транспорт Москвы |
| Заказчик | Хакатон (трамвайный трек) |
| Команда | Максим Богуславский (Backend+ML), Максим Баев (Frontend), Света Драчева (Analyst/QA/Docs) |
| Стек | Python 3.12, FastAPI, PostgreSQL+Timescale, ML: torch/xgboost/lightgbm/catboost, Frontend: Vite/React/TS |
| Toolchain | uv + ruff + mypy strict + vite + vitest + tsc + eslint + Orval + **pyscn** (structural quality) + **DBML** (schema tracking) |
| Методология | TDD, contract-first, data-agnostic, knowledge capture (ledger) |

## Architecture (1-минутная версия)

```
ML скрипты (вне Docker) → артефакты на диск → API (FastAPI) → Frontend (Vite/React)
                                              ↘ LLM Assistant ↘ MCP server (stdio)
```

ML пайплайн (`ml/`) запускается через `make train-*` / `make predict`.
API (`apps/backend/`) читает артефакты по JSON Schema контракту (`docs/schemas/`).
LLM Assistant (`apps/assistant/`) — lawcopilot-паттерн (LiteLLM + Reasoning + tools).
MCP (`apps/mcp/`) — stdio JSON-RPC сервер, обёртка над assistant tools.

## Directory Structure

```
hackathon/
├── apps/
│   ├── backend/          # FastAPI gateway :8000 (Богуславский)
│   ├── frontend/         # Vite/React/TS :5173 (Баев)
│   ├── assistant/        # LLM ассистент (LiteLLM-паттерн, lawcopilot)
│   └── mcp/              # MCP-сервер (stdio JSON-RPC, черновик)
├── ml/                   # ML скрипты (вне Docker) — train/predict/calibrate/montecarlo
├── docs/
│   ├── HANDOFF.md        # источник истины для трансфера контекста между сессиями
│   ├── ledger/           # append-only решения и находки (decisions.jsonl, findings.jsonl)
│   ├── notes/            # формат NNN-slug.md (из mlaw-rag)
│   ├── backlog/          # T-001..T-090 тикеты в YAML frontmatter (из candidate-tracker)
│   ├── api/openapi.json  # генерируется backend
│   ├── schemas/          # JSON Schema контракты артефактов
│   ├── prompts/          # промпты для сбора данных, EDA, валидации
│   └── reports/          # метрики и графики моделей
├── data/                 # .gitignore: synthetic/, real/
├── predictions/          # .gitignore: выход predict.py
├── .clinerules/          # 16 clinerules файлов (см. .clinerules/00-AGENTS.md)
├── .githooks/            # pre-commit, pre-push, commit-msg
├── Makefile              # единая точка входа
└── AGENTS.md             # этот файл
```

## Tech Stack

| Слой | Технология | Обоснование |
|---|---|---|
| ML | torch, polars, lightgbm, xgboost, catboost, pytorch-geometric, scikit-learn | Переиспользование кода из contest/ecup26-user-value |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2 | Шаблон из candidate-tracker |
| Frontend | Vite, React 18, TypeScript strict, TanStack Query/Router/Table, Recharts, react-leaflet | Шаблон из candidate-tracker |
| LLM | LiteLLM, Anthropic SDK, aiohttp | Шаблон из lawcopilot |
| MCP | mcp>=2.0.0 | stdio JSON-RPC |
| DB | PostgreSQL 16 + TimescaleDB 2.x | Временные ряды predictions/actuals |
| Cache | Redis 7 | Кэш API ответов |
| Tooling | uv 0.5+, ruff 0.5+, mypy 1.10+, yarn 4 (corepack), vite 5+, vitest, tsc 5+, eslint 9+ flat config | Из candidate-tracker 08-tooling.md |

## Commands (шпаргалка)

| Задача | Команда |
|---|---|
| Установить всё | `make install` |
| Хуки | `make hooks-install` |
| Поднять docker (backend+db+redis+frontend) | `make up` |
| Сгенерить синтетику | `make seed` |
| Обучить модель | `make train-baseline` / `train-xgboost` / `train-gru` / `train-hybrid` |
| Предсказать | `make predict` |
| Калибровка | `make calibrate` |
| Monte Carlo сценарий | `make mc-scenario` |
| Экспорт OpenAPI | `make api-gen` |
| Генерация TS типов (Orval) | `make fe-gen` |
| Линт | `make lint` |
| Типы | `make typecheck` |
| Тесты | `make test` |
| Полный check | `make check-all` |
| Топ-5 тикетов | `make backlog-ready` |
| Обновить HANDOFF | `make handoff-update` |
| Добавить решение в ledger | `make ledger-add` |
| Запустить MCP | `make mcp-run` |
| pyscn структурный анализ | `make pyscn` → `.pyscn/report.{json,html}` |
| pyscn vs baseline (CI gate) | `make pyscn-compare` |
| DBML schema из моделей | `make arch-dbml` → `docs/architecture/schema.{dbml,tables.md}` |
| Smoke benchmark BaselineMean | `make benchmark-baseline` |
| Полный benchmark grid | `make benchmark-all` |
| Запустить assistant smoke | `make assistant-test` |

## Quick Rules (полный список — в `.clinerules/`)

1. **Data-agnostic:** все источники за интерфейсом `DataSource`. Синтетика сейчас, реальные данные — на хакатоне.
2. **Contract-first:** JSON Schema артефактов фиксируется ДО данных. OpenAPI — ДО фронта.
3. **ML вне Docker:** обучение скриптами, артефакты на диск. API читает файлы.
4. **Knowledge capture:** каждое решение (RICE > 5) → `docs/ledger/decisions.jsonl`. Каждая находка → `docs/ledger/findings.jsonl`.
5. **Handoff:** каждый ответ заканчивается блоком `## CONTEXT HANDOFF` или обновляет `docs/HANDOFF.md`.
6. **Conventional Commits:** обязательны (enforced by `commit-msg` hook).
7. **Pre-commit:** ruff + prettier + проверка ledger.
8. **Pre-push:** mypy strict + pytest + orval-check.
9. **Memory budget:** не читать JSON > 1MB, не читать yarn.lock/uv.lock. Использовать `use_skill` для длинных инструкций.
10. **TDD:** RED → GREEN → REFACTOR для каждого тикета.

## Task Tracking

- Backlog: `docs/backlog/tickets/T-NNN-*.md` (YAML frontmatter + RICE)
- Top-5 ready: `make backlog-ready`
- Status: `docs/backlog/STATUS.md`
- Archive: `docs/backlog/archive/` (после `done`)

## Knowledge Capture

- Decisions: `docs/ledger/decisions.jsonl` (формат: id, ts, title, context, decision, alternatives, consequences, tickets, tags)
- Findings: `docs/ledger/findings.jsonl` (формат: id, ts, title, context, evidence, tickets, tags)
- Notes: `docs/notes/NNN-slug.md` (формат: finding → impact on decisions)
- Skills: `ai/skills/NN-name.md` (длинные инструкции, подключаются через `use_skill`)

Правила промоушена находок — в `.clinerules/15-promote-finding.md`.

## Don't do

- ❌ Использовать `npm install` или `pnpm install` (только `yarn` через corepack)
- ❌ Использовать `pip install` напрямую (только `uv`)
- ❌ Писать реальные ключи в `.env.example` (только плейсхолдеры `your_key_here`)
- ❌ Коммитить `.env`, `ml/artifacts/`, `predictions/`, `data/` (всё в .gitignore)
- ❌ Патчить сгенерированный код (`apps/frontend/src/generated/`)
- ❌ Skip `--no-verify` без причины
- ❌ Читать `yarn.lock` или `uv.lock` в контекст
- ❌ Обучать модели в Docker (только скриптами)
- ❌ Делать PR без обновлённого HANDOFF.md (если сессия длинная)

## Cross-References

- **Cline rules:** [`.clinerules/00-AGENTS.md`](.clinerules/00-AGENTS.md)
- **Backlog:** [`.clinerules/03-backlog-format.md`](.clinerules/03-backlog-format.md)
- **Tooling:** [`.clinerules/06-tooling.md`](.clinerules/06-tooling.md)
- **Handoff:** [`.clinerules/13-context-transfer.md`](.clinerules/13-context-transfer.md)
- **Ledger:** [`.clinerules/14-decisions-ledger.md`](.clinerules/14-decisions-ledger.md)
- **Promote:** [`.clinerules/15-promote-finding.md`](.clinerules/15-promote-finding.md)
- **Memory budget:** [`.clinerules/MEMORY-BUDGET.md`](.clinerules/MEMORY-BUDGET.md)
