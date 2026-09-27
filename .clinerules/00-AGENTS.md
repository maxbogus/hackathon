# Cline Project Rules — Transit-AI (hackathon)

Этот проект использует **contract-first**, **data-agnostic**, **ML-вне-Docker**, **knowledge capture (ledger)**.
Перед началом работы прочитай все файлы в `.clinerules/`.

## Index of clinerules

| # | File | Purpose |
|---|---|---|
| 00 | `00-AGENTS.md` | Мастер-индекс + entry point |
| 01 | `01-philosophy.md` | Data-driven, minimal scope, MVP first |
| 02 | `02-architecture.md` | Монорепо apps/*, контракты артефактов, ML вне Docker |
| 03 | `03-backlog-format.md` | YAML frontmatter spec + RICE + workflow |
| 04 | `04-secret-handling.md` | Секреты НИКОГДА в git, .env.example с плейсхолдерами |
| 05 | `05-hackathon-rules.md` | Hard rules хакатона (T-001..T-090, no LLM >4B, etc.) |
| 06 | `06-tooling.md` | uv + ruff + mypy + yarn 4 + vite + vitest + tsc + orval |
| 07 | `07-workflows.md` | Commit / PR / handoff / promotion |
| 08 | `08-contracts-and-artifacts.md` | JSON Schema, OpenAPI, MCP контракты |
| 09 | `09-map-strategy.md` | OSM ↔ Yandex переключение через env |
| 10 | `10-ml-as-scripts.md` | Почему ML не в Docker, контракт через файлы |
| 11 | `11-assistant-pattern.md` | lawcopilot-паттерн, LiteLLM, Reasoning, tools |
| 12 | `12-mcp-draft.md` | Что в черновике MCP, что нет, как подключать |
| 13 | `13-context-transfer.md` | HANDOFF.md, блок CONTEXT HANDOFF, трансфер сессии |
| 14 | `14-decisions-ledger.md` | Фиксация решений в ledger (RICE > 5) |
| 15 | `15-promote-finding.md` | Находка → note → rule → skill |
| 16 | `16-tdd-cycle.md` | RED → GREEN → REFACTOR |
| 17 | `17-pyscn-quality-gate.md` | pyscn structural analyzer (CI gate) |
| 18 | `18-dbml-schema-tracking.md` | DBML schema as code |
| 19 | `19-ml-benchmark-pipeline.md` | ML benchmark pipeline (offline) |
| 20 | `20-text-constants-registry.md` | Frontend hybrid t(key) text registry |
| 21 | `21-runtime-uv.md` | uv как единый package manager (Python↔Docker↔ML) |
| 22 | `22-load-testing.md` | k6 load testing rules (smoke/baseline/stress/spike/soak, R6 SLA) |
| 23 | `23-submission-versioning.md` | Submission = (date-range, model-version, run-ts) + manifest.json (F-021) |
| 24 | `24-ml-candidate-output.md` | SUBMISSION CANDIDATE block после каждого ML запуска (T-149) |
| 25 | `25-poi-radius-selection.md` | Per-category радиусы POI по реальным расстояниям (T-168, D-024) |
| 26 | `26-per-route-feature-aggregation.md` | Per-stop → per-route mean aggregation для route-only XGBoost (D-025) |
| 27 | `27-wape-score-vs-wape.md` | WAPE ∈ [0,+∞) vs WAPE-score ∈ [0,1] = 1-WAPE (F-033) |
| 28 | `28-submission-workflow-local-vs-platform.md` | Submission workflow: sanity-check 5 критериев + drift учёт (F-039, F-040) |
| 29 | `29-zsh-shell-quirks.md` | zsh на Ubuntu — gotchas с `{}`, f-string в `-c "..."`, heredoc vs bash |
| 30 | `30-no-replay-submissions.md` | Не предлагать варианты, которые уже залиты на платформу (F-061, D-027) |
| 31 | `31-passenger-mode-actuals-and-predictions.md` | PassengerMode показывает actuals + predictions рядом (T-218, fallback MAX period) |
| — | `MEMORY-BUDGET.md` | Анти-краш: не читать >1MB JSON |

## Quick rules

1. **Workspace:** `apps/*` ↔ `ml/` ↔ `scripts/`. Не делать циклические импорты.
2. **Python:** ruff + mypy strict + pytest-asyncio. Перед handoff — `make lint`.
3. **TypeScript:** strict mode, no implicit `any`, ESLint flat config.
4. **Node:** Yarn 4 (Berry) через corepack. **NO npm install, NO pnpm install**.
5. **Commits:** Conventional Commits (enforced `.githooks/commit-msg`).
6. **Tasks:** Работать только с `docs/backlog/tickets/T-NNN.md` где `status: ready`.
   При старте менять на `status: in-progress`.
7. **Contracts:** Backend-first. `apps/frontend/src/generated/**` — read-only вывод.
   Менять FastAPI routes/schemas, потом `make api-gen` + `make fe-gen`.
8. **Docs:** Всё в `docs/`. Backlog с YAML frontmatter. ADR в `docs/backlog/decisions/`.
9. **Ledger:** Каждое решение RICE > 5 → `docs/ledger/decisions.jsonl`.
   Каждая находка → `docs/ledger/findings.jsonl`. Через `make ledger-add`.
10. **Handoff:** В конце каждого ответа — блок `## CONTEXT HANDOFF` (6 строк)
    или обновление `docs/HANDOFF.md` (источник истины для новой сессии).
11. **Frontend text registry:** все UI-строки через `t(key)` из `apps/frontend/src/lib/i18n/`
    (см. clinerule 20). Запрет хардкода русских строк в `.tsx` вне `lib/i18n/`.
12. **Tooling split:** Python (backend, ml, assistant, mcp, scripts) → **uv 0.5.7+**,
    локально И в Docker backend (см. clinerule 21). Frontend → **yarn 4 corepack**.
    Никакого `pip install`, `python script.py` напрямую, `npm install`, `pnpm install`.
13. **Makefile — single entry point:** все Python-скрипты (кроме фронтовых) подключены
    через `make <target>`. WIP-цели помечены `[WIP: T-NNN]` в help.
14. **Load testing:** k6 запускается ТОЛЬКО в Docker (профиль `loadtest`), через
    `make loadtest-*`. SLA gate — `make loadtest-check`. R6: p95 ≤ 2000ms, err ≤ 1%.
    Подробности — `.clinerules/22-load-testing.md`.
15. **Shell = zsh на Ubuntu:** не bash. Brace expansion `{i}`, f-string в
    `python3 -c "..."`, heredoc — всё ломается по-разному. Подробности —
    `.clinerules/29-zsh-shell-quirks.md`. Использовать editor tool для правок
    файлов вместо shell sed/python heredoc когда возможно.
16. **No replay submissions (F-061):** перед тем как предложить пользователю
    "3 варианта X" — прочитать `docs/ledger/findings.jsonl` (last 14d),
    `docs/HANDOFF.md` секции "Не делать" + "Если есть время", `predictions/*.json`
    манифесты. Sweep вокруг найденного peak (например `pred≤N` для разных N) ≠ новые
    варианты. Каждый предложенный вариант должен иметь `novelty` ∈
    {validated, in_progress, partial, untested, queued}. Если 0 untested — СТОП
    + сообщить "стратегия исчерпана". Подробности — `.clinerules/30-no-replay-submissions.md`.

## How Cline should work on this project

1. **Перед стартом задачи:** прочитай `docs/HANDOFF.md` (если есть) и `docs/backlog/STATUS.md`.
2. **Прочитай нужный clinerule** (не все 16 сразу — это сожрёт контекст).
3. **Найди топ-3 тикета** через `make backlog-ready`.
4. **Пометь `status: in-progress`** в YAML frontmatter выбранного тикета.
5. **Реализуй** по правилам архитектуры (см. `02-architecture.md`).
6. **RED → GREEN → REFACTOR** (см. `16-tdd-cycle.md`).
7. **Запусти `make check-all`** перед handoff.
8. **Закоммить** с Conventional Commits (см. `commit-msg` hook).
9. **Обнови ADR** если архитектура меняется (`docs/backlog/decisions/0XX-*.md`).
10. **Обнови HANDOFF.md** через `make handoff-update` или блоком в ответе.

## Memory Budget (КРИТИЧНО — прочитай `MEMORY-BUDGET.md`)

> Лимит контекста: ~192K токенов. System prompt ~66KB (~20K токенов).
> **Бюджет на работу: ~170K токенов.**

| Rule | Action |
|------|--------|
| ❌ **NEVER** | `read_file()` на JSON > 1MB (история чата, логи) |
| ❌ **NEVER** | `read_file()` на `yarn.lock`, `uv.lock` |
| ⚠️ **Use** | `execute_command("python3 ...")` + grep/jq для больших файлов |
| ⚠️ **Use** | `use_skill` для длинных инструкций (RED→GREEN, sweep) |
| ✅ **SAVE** | Промежуточные результаты в файлы, не в контекст |

## Don't do

- ❌ Использовать `npm install` или `pnpm install` (только `yarn` через corepack)
- ❌ Использовать `pip install` напрямую (только `uv`)
- ❌ Писать реальные ключи в `.env.example` (только плейсхолдеры)
- ❌ Коммитить `.env`, `ml/artifacts/`, `predictions/`, `data/` (в .gitignore)
- ❌ Патчить сгенерированный код (`apps/frontend/src/generated/`)
- ❌ Skip `--no-verify` без причины
- ❌ Читать `yarn.lock` или `uv.lock` в контекст
- ❌ Обучать модели в Docker (только скриптами)
- ❌ Использовать LLM > 4B параметров для inference (есть правило R2 в hackathon-rules)
- ❌ Делать PR без обновлённого HANDOFF.md (если сессия длинная)
- ❌ Запускать Python-скрипты в обход Makefile (только через `make <target>`)
- ❌ Использовать `python` или `pip` напрямую (только `uv run ...`)
