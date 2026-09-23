# STATUS.md — критический путь

_Обновлено: 2026-09-23. После T-127: backend `/api/v1/predictions/eta` готов (23 теста, live curl OK, контракт синхронизирован с фронтом через Orval). Зафиксировано: D-011 (STOP_ROUTES mock-match), F-011 (отсутствовал customInstance.ts — создан). Очередь: T-128 (capacity-aware load_pct), T-131 (dispatcher alerts), T-115 (README)._

## Сводка

| Счётчик | Значение |
|---|---|
| Тикетов в `archive/` (done за всё время) | **35** |
| Тикетов в `tickets/`: | **17** |
| &nbsp;&nbsp;• `ready` (готовы к старту) | **17** |
| &nbsp;&nbsp;• `backlog` (отложены) | **0** |
| &nbsp;&nbsp;• `in-progress` | **0** |
| Решений в ledger (`decisions.jsonl`) | **11** (D-001..D-011) |
| Находок в ledger (`findings.jsonl`) | **11** (F-001..F-008, F-009, F-010, F-011) |

## Готовые к старту (топ-5 по RICE score)

| ID | RICE | Усилие | Что |
|---|---|---|---|
| **T-115** | 10.00 | 1h | README: добавить English version, раздел Handover, починить ссылки |
| **T-128** | 8.40 | 2h | `load_pct` прогноз с учётом capacity трамвая |
| **T-131** | 8.10 | 2h | Алерты диспетчеру T-30 мин warning |
| **T-135** | 6.0 | 2h | TanStack Router: перевести role-switcher на URL (зависит от T-129) |
| **T-123** | 5.5 | 3h | Weather data integration (Open-Meteo) |

> Цепочка `T-127 → T-128 → T-129 → T-130` — все архивированы. Демо жюри готово на backend+frontend стеке.
> Следующие блокеры: T-128 (capacity для load_pct), T-131 (dispatcher UI).

## Backlog (отложены)

_Пусто — все тикеты либо в `ready`, либо в `archive`._

## В работе (in-progress)

_Пусто._

## Последние архивированные (для контекста)

- T-127 — backend GET `/api/v1/predictions/eta?stop_id=X&n=3` (1h, 23 теста) ✨ новый
- T-129 — frontend режим «Пассажир» — React/Vite UI для ETA + load + рекомендация (1h)
- T-133 — слайд «Боли пассажиров → наше решение» для жюри (1h)
- T-130 — recommend() бизнес-логика «ехать/ждать» для frontend (1h) ✨ новый
- T-091 — fix mypy exclude regex (F-001)
- T-042 — backend GET `/api/v1/predictions/stop/{id}/route/{id}` (3h)
- T-039 — ml benchmark scripts + api-gen scripts (5h)
- T-037 — ml reports/plots.py matplotlib headless Agg (3h)
- T-035 — ml evaluate.py RMSLE/MAE/MAPE (4h)
- T-034 — ml calibrate.py per-bucket biases (4h)
- T-033 — ml predict.py → parquet (3h)
- T-032 — ml train.py + scripts/train_baseline.py (5h)
- T-031 — ml training registry + meta.json artifact contract
- T-028, T-027, T-025, T-024, T-023 — ML data + models базовый набор
- T-014, T-019, T-020, T-021, T-022 — backend skeleton
- T-001..T-013 — Phase 0 toolchain + clinerules + ledger

## Открытые вопросы

_Пусто — все мёртвые ссылки (T-098/T-094/T-047/T-131-ui/T-117) убраны преднамеренно (см. D-008)._

## Tooling добавлено в Phase 1

- ✅ **pyscn** 1.32.0 (structural quality gate): clinerule 17, Makefile `pyscn` / `pyscn-compare` / `pyscn-baseline`, pre-push hook
- ✅ **DBML schema tracking**: clinerule 18, Makefile `arch-dbml` / `arch-dbml-check`, scripts/generate_dbml.py
- ✅ **ML benchmark pipeline**: clinerule 19, ml/transit_ai/benchmark/{configs,runner,cli,report,compare}.py, scripts/{benchmark_baseline,benchmark_all}.py
- ✅ **Docker**: docker-compose.yml + apps/{backend,frontend}/Dockerfile

## Решения в ledger (RICE > 5)

| ID | Решение | RICE |
|---|---|---|
| D-001 | ML вне Docker (scripts + artefacts on disk) | ~12 |
| D-002 | lawcopilot-паттерн для ассистента | ~8 |
| D-003 | MapProvider Strategy (OSM ↔ Yandex через env) | ~7 |
| D-004 | Knowledge Capture (ledger + handoff + promotion) | ~10 |
| D-005 | Переиспользование из contest/ecup26-user-value | ~8 |
| D-007 | Удалить T-116, отложить T-115/T-130 до данных | — |
| D-008 | Убрать мёртвые ссылки T-098/T-094/T-047/T-131-ui/T-117 | — |
| D-009 | Отказаться от Streamlit UI → React/Vite (T-129/T-130) | — |
| D-010 | apps/frontend nodeLinker=node-modules (фикс EBADF под vitest@2) | — |
| **D-011** | **STOP_ROUTES hardcoded match frontend mock (pixel-perfect demo)** | — ✨ новый |

## Риски

| Риск | Вероятность | Импакт | Стратегия |
|---|---|---|---|
| Данные от организаторов в неожиданном формате | Средняя | Высокий | Гибкие парсеры в RealSource (T-026) + fallback стратегии |
| Максим №1 перегружен (Backend+ML) | Высокая | Высокий | Помощь от Максима №2 на API слое, Света — на валидации |
| Не успеваем GCN | Средняя | Низкий | COULD-фича (RICE < 5), есть fallback — XGBoost + Hybrid |
| README имеет битые ссылки | Средняя | Средний | T-115 в топ-3 ready, чинит за 1 час |
