# STATUS.md — критический путь

_Обновлено: 2026-09-25 22:00 (T-168 done, F-033..F-043 + T-171 in-progress, 48h до дедлайна 27.09). После Q-A сессии: route 5 исключён (только 9 маршрутов, F-041), predictions округлены до integer (F-042), дедлайн 27.09 (F-043). Submission #9 готов: `submission_xgboost_v8_poi_20251101_20251231_20260925T191625Z.csv` (13176 строк, 9 маршрутов, int). Holdout WAPE-score=0.8751 (calibrated). Ждём заливки и platform score (предыдущий best v6=0.12253)._

## Сводка

| Счётчик | Значение |
|---|---|
| Тикетов в `archive/` (done за всё время) | **51** (+T-137/T-160/T-161/T-163/T-165/T-167/T-222/T-226) |
| Тикетов в `tickets/`: | **30** (+T-220, T-221, T-224 — T-223 отменён, T-222/T-226 done) |
| &nbsp;&nbsp;• `ready` (готовы к старту) | **31** |
| &nbsp;&nbsp;• `backlog` (отложены) | **0** |
| &nbsp;&nbsp;• `in-progress` | **0** |
| Решений в ledger (`decisions.jsonl`) | **24** (D-001..D-023) |
| Находок в ledger (`findings.jsonl`) | **40** (F-001..F-043) |
| Решений в ledger (`decisions.jsonl`) | **30** (D-001..D-040) |

## Готовые к старту (топ-5 по RICE score)

| ID | RICE | Усилие | Что |
|---|---|---|---|
| **T-115** | 10.00 | 1h | README Russian + Handover (scope-down: без English) |
| **T-125** | 5.40 | 2h | Feature engineering: weather + traffic фичи |
| **T-122** | 2.70 | 4h | MapProvider + LeafletMap + YandexMap (следующая цель после T-135) |
| **T-134** | 2.50 | 2h | backend predictions route horizon=month |
| **T-138** | 2.50 | 2h | ML submission pipeline end-to-end |

> Блок валидации R3+R6 хакатона завершён (T-160..T-167). Цепочка `T-127 → T-128 → T-129 → T-130 → T-131 → T-141 → T-135` — все архивированы. Демо жюри готово: ETA + capacity + alerts + text registry + URL routing + load testing + SLA gate + HACKATHON_CHECKLIST.md.

## Backlog (отложены)

_Пусто — все тикеты либо в `ready`, либо в `archive`. Из 22 ready в топ-15 попали 6 (T-122, T-125, T-134, T-137, T-138, T-139)._

## В работе (in-progress)

_Пусто (готовы брать T-115 / T-137 / T-125 / T-122)._

## Последние архивированные (для контекста)

- **T-135** — TanStack Router URL routing (5 file-based маршрутов + `<RouterProvider>` singleton + `<Link>` nav + `defaultPreload: 'intent'`, 6+2 новых тестов, 60/60 frontend зелёные, F-014 зафиксирован) ✨ новый
- T-141 — frontend text registry hybrid t(key) (`apps/frontend/src/lib/i18n/` × 5 файлов мигрированы, 17 i18n тестов, 55/55 frontend зелёные, `make frontend-text-check` gate)
- T-131 — dispatcher overload alerts (`/insights/alerts` + AlertsPanel + 21+3 теста)
- T-128 — capacity-aware load_pct (TRAM_CAPACITY, compute_load_pct, load_color, +20 тестов)
- T-127 — backend GET `/api/v1/predictions/eta?stop_id=X&n=3` (1h, 23 теста)
- T-129 — frontend режим «Пассажир» — React/Vite UI для ETA + load + рекомендация (1h)
- T-133 — слайд «Боли пассажиров → наше решение» для жюри (1h)
- T-130 — recommend() бизнес-логика «ехать/ждать» для frontend (1h)
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
| D-011 | STOP_ROUTES hardcoded to match frontend mock | — |
| D-012 | TRAM_CAPACITY в `forecast/load.py` | — |
| D-013 | Dispatcher alerts polling via TanStack Query | — |
| D-014 | Hybrid text registry `t(key)` без `react-i18next` | ~6 |
| D-009 | Отказаться от Streamlit UI → React/Vite (T-129/T-130) | — |
| D-010 | apps/frontend nodeLinker=node-modules (фикс EBADF под vitest@2) | — |
| **D-011** | **STOP_ROUTES hardcoded match frontend mock (pixel-perfect demo)** | — |
| **D-012** | **TRAM_CAPACITY в forecast/load.py (не config.py — domain constant)** | — |
| **D-013** | **Dispatcher alerts polling: setInterval via TanStack Query, не streamlit-autorefresh (+ /insights/alerts URL)** | — |
| **D-014** | **Hybrid text registry `t(key)` без библиотек: `apps/frontend/src/lib/i18n/` + grep CI gate** | ~6 ✨ новый |

## Риски

| Риск | Вероятность | Импакт | Стратегия |
|---|---|---|---|
| Данные от организаторов в неожиданном формате | Средняя | Высокий | Гибкие парсеры в RealSource (T-026) + fallback стратегии |
| Максим №1 перегружен (Backend+ML) | Высокая | Высокий | Помощь от Максима №2 на API слое, Света — на валидации |
| Не успеваем GCN | Средняя | Низкий | COULD-фича (RICE < 5), есть fallback — XGBoost + Hybrid |
| README имеет битые ссылки | Средняя | Средний | T-115 в топ-3 ready, чинит за 1 час |
