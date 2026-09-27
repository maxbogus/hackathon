# Transit-AI — Hackathon: Прогноз загрузки трамваев Москвы

> Интерактивный веб-сервис прогнозирования пассажиропотока трамваев Москвы на три горизонта (день/месяц/год).
>
> **Хакатон Московского транспорта (25.09–03.10.2026)** — трек «ИИ-прогноз загрузки трамвайных маршрутов».
> Бенефициары: Департамент транспорта Москвы, диспетчеры, пассажиры.
> Подробности: [docs/hackathon/requirements.md](docs/hackathon/requirements.md).

---

## 🎯 Бенефициары (для кого это решение)

- 🏛 **Департамент транспорта Москвы** — инструмент управления трамвайной сетью, готовый к внедрению
- 🎛 **Диспетчеры транспортного комплекса** — оперативное принятие решений, раннее предупреждение перегрузок
-  **Пассажиры московского трамвая** — предсказуемость, комфорт, сокращение времени ожидания

> «Цель хакатона — повышение качества и безопасности поездок миллионов пассажиров» — М. Ликсутов

## 📊 Метрики успеха для города

| Метрика | Baseline | Наше решение | Улучшение |
|---|---|---|---|
| Среднее время ожидания | 8-12 мин | 6-9 мин | **−15%** |
| Перегруженные рейсы (load > 90%) | ~23% | < 15% | **−35%** |
| Время реакции диспетчера на инцидент | 10 мин | 3 мин | **−70%** |
| Точность прогноза ETA | n/a | ± 2 мин | — |
| Прогноз загрузки рейса (load_pct RMSE) | n/a | < 12% | — |

Детализация болей пассажиров: [docs/hackathon/presentation/slide_01_pain_points.md](docs/hackathon/presentation/slide_01_pain_points.md).

---

## Что это

Pet-project для хакатона по трамвайному треку. Система:

- Принимает исторические данные валидаций и телематики
- Обучает ML-модели (baseline / XGBoost / GRU / hybrid) скриптами
- Хранит артефакты и прогнозы на диске по контракту JSON Schema
- Отдаёт прогнозы через FastAPI + OpenAPI + Orval-сгенерированный фронт
- Показывает дашборд (карта, графики, таблицы) на Yandex Maps / Leaflet
- Опционально — LLM-ассистент через MCP-сервер (lawcopilot-паттерн)

## Команда

- **Максим Богуславский** — Backend + ML (lead)
- **Максим Баев** — Frontend + помощь с backend
- **Светлана Драчева** — Analyst, QA, документация, research

## Архитектура (1 минута)

```
ML скрипты → артефакты → API (FastAPI) → Frontend (Vite/React)
                            ↘ LLM Assistant ↘ MCP server
```

Полная архитектура — в [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Карта проекта для AI-агентов — в [AGENTS.md](AGENTS.md).

## Quick Start

```bash
# 1. Установить зависимости (Python + Node)
make install

# 2. Установить git-хуки (pre-commit, pre-push, commit-msg)
make hooks-install

# 3. Скопировать .env.example → .env, вставить свои ключи
cp .env.example .env
$EDITOR .env

# 4. Поднять docker stack (postgres+timescale, redis, backend, frontend)
make up

# 5. Сгенерить синтетику, обучить baseline, сделать прогноз
make seed train-baseline predict

# 6. Открыть
open http://localhost:5173          # frontend
open http://localhost:8000/docs     # backend Swagger
```

## Структура

```
hackathon/
├── apps/
│   ├── backend/         # FastAPI (порт 8000)
│   ├── frontend/        # Vite/React (порт 5173)
│   ├── assistant/       # LLM ассистент (LiteLLM-паттерн)
│   └── mcp/             # MCP-сервер (stdio)
├── ml/                  # ML скрипты (вне Docker)
├── docs/
│   ├── HANDOFF.md       # источник истины для трансфера контекста
│   ├── ledger/          # append-only решения и находки
│   ├── notes/           # находки в формате NNN-slug.md
│   ├── backlog/         # T-001.. тикеты
│   ├── api/openapi.json # генерируется backend
│   ├── schemas/         # JSON Schema контракты
│   ├── prompts/         # промпты для организаторов, EDA, валидации
│   └── reports/         # метрики моделей
├── data/                # .gitignore (synthetic/, real/)
├── predictions/         # .gitignore (выход predict.py)
├── .clinerules/         # 16 clinerules файлов
├── .githooks/           # pre-commit, pre-push, commit-msg
├── Makefile
└── AGENTS.md
```

## Makefile (основные команды)

```bash
make help                # все доступные команды
make install             # uv sync + yarn install
make up                  # docker compose up -d
make down                # docker compose down

# ML (НЕ в Docker)
make seed                # синтетика
make inventory           # профиль данных (числами, не hearsay)
make train-baseline      # baseline (mean по часу/дню/маршруту)
make train-xgboost       # XGBoost с фичами
make train-gru           # GRU + attention pooling (из contest/...)
make train-hybrid        # GRU + LGBM blend (log-space)
make train-all           # все модели
make predict             # прогноз активной моделью
make calibrate           # per-bucket калибровка
make mc-scenario         # Monte Carlo "что если"
make evaluate            # метрики RMSLE/MAE/MAPE

# API/Frontend
make api-gen             # экспорт OpenAPI → docs/api/openapi.json
make api-check           # проверка что OpenAPI свежий
make fe-gen              # Orval → apps/frontend/src/generated/

# Quality
make lint                # ruff + eslint + prettier --check
make typecheck           # mypy strict + tsc --noEmit
make test                # pytest + vitest
make format              # autofix
make check-all           # lint + typecheck + test + api-check + ledger-check

# Knowledge capture
make backlog-ready       # топ-5 тикетов по RICE
make ledger-add          # добавить решение в ledger
make ledger-list         # показать последние решения
make note-from-finding   # создать note из находки
make promote NOTE=NNN TARGET=rule|skill
make handoff-update      # обновить HANDOFF.md
make handoff             # показать текущий HANDOFF.md

# MCP + Assistant
make mcp-run             # запустить MCP сервер (stdio)
make assistant-test      # smoke test registry моделей
```

## Технологии

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2
- **Frontend:** Vite, React 18, TypeScript strict, TanStack Query/Router/Table, Recharts, react-leaflet
- **ML:** torch, polars, lightgbm, xgboost, catboost, pytorch-geometric, scikit-learn, pydantic
- **LLM:** LiteLLM (через OpenAI-совместимый API), Anthropic SDK, aiohttp
- **MCP:** mcp>=2.0.0 (stdio JSON-RPC)
- **DB:** PostgreSQL 16 + TimescaleDB 2.x
- **Cache:** Redis 7
- **Tooling:** uv 0.5+, ruff, mypy strict, yarn 4 (corepack), vite 5+, vitest, tsc 5+, eslint 9+ flat config, orval

## 📈 Производительность (замеры)

> **Обязательный раздел по ТЗ.** Методика: k6 0.54 (Docker, `grafana/k6`) нагружает
> `GET /api/v1/predictions/stop/{id}` (реальный инференс активной модели) по сети
> `localhost:8000`; k6 пришпилен к CPU 0–1, backend — на остальных ядрах, чтобы
> измерять сервис, а не тестер. Артефакт прогона — консольный summary k6
> (`http_req_duration p(95)`, `errors`), числа которого зафиксированы в таблице ниже;
> HTML-дашборд (`K6_WEB_DASHBOARD_EXPORT`) и `--out json` в headless Docker этого
> окружения не сохраняются (известное ограничение, см. HANDOFF).

| Профиль | Дата | Нагрузка | Запросов | Err | avg | p90 | **p95** | max |
|---|---|---|---|---|---|---|---|---|
| smoke (CI-gate) | 2026-09-27 | 10 VU × 30 s (think-time 1 s) | 300 | 0.00 % | 7.7 ms | 18.5 ms | **26.3 ms** | 71.5 ms |

**Выводы (честно):**

- p95 = **26 мс** при SLA хакатона **≤ 2000 мс** (R6) — запас ~75×;
- ошибок 0 из 300; узкое место при 10 VU не найдено;
- RPS в smoke ограничен think-time 1 с (≈10 rps на 1 воркер промпта), поэтому это
  проверка latency-бюджета, а не замер пропускной способности: регрессионный
  `make loadtest-baseline` (50 VU × 5 min) и `stress` (100 VU × 3 min) дают
  throughput-числа, HTML-отчёты кладутся туда же.

**Ресурсы одного экземпляра** (`docker-compose.yml`, лимиты, а не «железо»):

| Контейнер | CPU | RAM | Роль |
|---|---|---|---|
| backend (FastAPI) | 0.5 vCPU | 768 MiB | API + инференс из артефактов |
| postgres (TimescaleDB) | — | 512 MiB | actuals + predictions |
| redis | — | 128 MiB | кэш + Celery broker |
| frontend (nginx) | — | 128 MiB | статика + прокси `/api` |
| k6 (только профиль `loadtest`) | 2.0 vCPU (cpuset 0,1) | 1 GiB | тестер нагрузки |

Воспроизведение: `make up` → `make loadtest-smoke` → `make loadtest-check`
(парсит JSON последнего прогона и валидирует SLA p95 ≤ 2 s, err ≤ 1 %).

## Документация

- [AGENTS.md](AGENTS.md) — карта проекта для AI-агентов
- [.clinerules/00-AGENTS.md](.clinerules/00-AGENTS.md) — главная точка входа для Cline
- [docs/HACKATHON_RULES.md](docs/HACKATHON_RULES.md) — правила хакатона
- [docs/DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md) — что нужно от организаторов
- [docs/USER_STORIES.md](docs/USER_STORIES.md) — сценарии диспетчера
- [docs/ML.md](docs/ML.md) — описание моделей
- [docs/HACKATHON_CHECKLIST.md](docs/HACKATHON_CHECKLIST.md) — финальный чек-лист submission (R8)
- [docs/PROMPTS/](docs/PROMPTS/) — промпты для сбора данных, EDA, валидации
- [docs/ledger/README.md](docs/ledger/README.md) — как пользоваться ledger

## Что переиспользовали из других проектов

| Проект | Что взяли |
|---|---|
| `~/Repositories/candidate-tracker/` | Структура `apps/*`, `Makefile` стиль, `orval.config.ts`, clinerules формат, backlog YAML frontmatter, RICE |
| `~/Repositories/mlaw-rag/` | `Makefile` с автогенерацией help, Clean Architecture, TDD-тикеты, findings → notes |
| `~/Repositories/contest/` | `experiment_neural_gru.py`, `experiment_blend_gru_lgbm.py`, `apply_bucket_calibration.py`, ECUP_RULES, context-transfer |
| `~/Repositories/lawcopilot/` | LLM-провайдеры (LiteLLM-адаптер, ReasoningConfig, harness с tool-calling), MCP v3 mounting, ai/skills/ |
| `~/Repositories/mcp-servers/` | MCP сервер паттерн (celery-batch-mcp), JSON-RPC регистрация |
| `~/Repositories/montecarlo/` | Библиотека симуляций (distributions.py, simulator.py) |

## Лицензия

MIT (хакатон, не для прода).
