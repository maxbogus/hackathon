# STATUS.md — критический путь

## Сводка

| Phase | Статус | Готовность |
|---|---|---|
| 0 — Toolchain + Clinerules + Ledger | 🟢 done | 100% (13/13 тикетов в archive) |
| 1 — Backend skeleton (FastAPI + Alembic + OpenAPI) | 🟡 in-progress | 1 in-progress, 8 ready |
| 2 — ML pipeline (scripts + artefacts) | 🟡 ready | 15 ready, 0 in-progress |
| 3 — Backend ↔ ML contract (loader + endpoints) | 🟡 ready | 0/10 |
| 4 — Frontend (Vite + Orval + Map + Dashboard) | 🟡 ready | 0/14 |
| 5 — LLM Assistant (lawcopilot-паттерн) | 🟡 ready | 0/9 |
| 6 — MCP draft | 🟡 ready | 0/4 |
| 7 — Docs + QA (Света) | 🟡 ready | 0/11 |
| 8 — CI + polish | 🟡 ready | 0/5 |

**Готово: 13/90 тикетов (14%). 24 тикета в `tickets/` (Phase 1: T-014..T-022, Phase 2: T-023..T-037).**

## Критический путь

```
Phase 0 (DONE) → Phase 1 (backend skeleton) → Phase 2 (ML) → Phase 4 (frontend MVP) → demo
                  T-014 → T-020 → T-022         T-025 → T-031 → T-038 → T-042 → T-048 → T-051 → done
```

Следующая критическая точка: T-014 (backend pyproject + main.py + config.py).

## Завершённые тикеты (Phase 0)

- T-001 — Repo init (AGENTS.md, README.md, .gitignore, .editorconfig)
- T-002 — Makefile (226 строк) + .env.example (83 строки, плейсхолдеры)
- T-003 — root pyproject.toml (uv workspace members: apps/backend, apps/assistant, apps/mcp, ml)
- T-004 — ruff + mypy strict в root pyproject.toml
- T-005 — .pre-commit-config.yaml (ruff + prettier + gitleaks + ledger-check)
- T-006 — .githooks/{pre-commit, pre-push, commit-msg} + install target
- T-007 — apps/frontend/package.json (vite + react + ts + tanstack + recharts + react-leaflet)
- T-008 — apps/frontend/{eslint.config.js, .prettierrc.json, vite.config.ts, vitest.config.ts}
- T-009 — .clinerules/{00-AGENTS, MEMORY-BUDGET, 01-philosophy}
- T-010 — .clinerules/{02-architecture, 08-contracts, 10-ml-as-scripts}
- T-011 — .clinerules/{13-context-transfer, 14-decisions-ledger, 15-promote-finding}
- T-012 — docs/backlog/{README, STATUS}.md + scripts/{new_ticket, ready_tickets}.py
- T-013 — docs/ledger/{decisions.jsonl (5 записей), findings.jsonl, README.md} + scripts/{ledger.py, note_from_finding.py, promote_note.py}

Все архивированы в `docs/backlog/archive/`.

## Готовые к старту (топ-5 по RICE)

| ID | Title | Score | Phase |
|---|---|---|---|
| T-023 | ml/ pyproject.toml full deps (torch, polars, xgboost, lightgbm, catboost) | 3.500 | 2 |
| T-019 | apps/backend forecast module stub + loader interface | 2.625 | 1 |
| T-028 | ml transit_ai models xgboost predictor | 2.625 | 2 |
| T-031 | ml transit_ai training registry meta.json artifact contract | 2.625 | 2 |
| T-035 | ml transit_ai training evaluate.py metrics (RMSLE, MAE, MAPE) | 2.625 | 2 |

## В работе (in-progress)

- **T-014** — apps/backend pyproject.toml + main.py + config.py

## Блокеры

Нет.

## Решения в ledger (RICE > 5)

- **D-001** ML вне Docker (RICE 12)
- **D-002** lawcopilot-паттерн для ассистента (RICE 8)
- **D-003** MapProvider Strategy (RICE 7)
- **D-004** Knowledge Capture (ledger + handoff + promotion) (RICE 10)
- **D-005** Переиспользование из contest/ecup26-user-value (RICE ~8)

## Риски

| Риск | Вероятность | Импакт | Стратегия |
|---|---|---|---|
| Данные от организаторов в неожиданном формате | Средняя | Высокий | Гибкие парсеры в RealSource (T-026) + fallback стратегии |
| Максим №1 перегружен (Backend+ML) | Высокая | Высокий | Помощь от Максима №2 на API слое, Света — на валидации |
| Не успеваем GCN | Средняя | Низкий | COULD-фича (RICE < 5), есть fallback — XGBoost + Hybrid |
