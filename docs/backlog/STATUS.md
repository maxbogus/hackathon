# STATUS.md — критический путь

_Обновлено: 2026-09-23. После чистки беклога: T-116 удалён, T-115 + T-130 → `backlog`._

## Сводка

| Счётчик | Значение |
|---|---|
| Тикетов в `archive/` (done за всё время) | **31** |
| Тикетов в `tickets/`: | **21** |
| &nbsp;&nbsp;• `ready` (готовы к старту) | **19** |
| &nbsp;&nbsp;• `backlog` (отложены) | **2** — T-115, T-130 |
| &nbsp;&nbsp;• `in-progress` | **0** |
| Решений в ledger (`decisions.jsonl`) | **7** (D-001..D-007) |
| Находок в ledger (`findings.jsonl`) | **6** (F-001..F-006) |

## Готовые к старту (топ-5 по RICE score)

| ID | RICE | Усилие | Что |
|---|---|---|---|
| **T-129** | 13.50 | 1h | Streamlit режим «Пассажир» — ETA + загрузка (Baev) |
| **T-133** | 12.00 | 1h | Слайд «Боли → Решение» для жюри |
| **T-128** | 8.40 | 2h | `load_pct` прогноз с учётом capacity трамвая |
| **T-131** | 8.10 | 2h | Алерты диспетчеру T-30 мин warning |
| **T-127** | 6.40 | 3h | Backend endpoint `/api/v1/predictions/eta` |

> Цепочка `T-127 → T-128 → T-129` — это полный путь к демо для жюри за ~6 часов работы.
> Зависимости T-127: T-019 ✅ (архив), T-033 ✅ (архив). См. «Открытые вопросы» насчёт T-098.

## Backlog (отложены до появления данных)

| ID | RICE | Причина откладывания |
|---|---|---|
| **T-115** | 10.00 | README с бенефициарами + handover — нет смысла без реальных метрик моделей |
| **T-130** | 13.50 | «Ехать или ждать?» — нужны реальные значения ETA/load для валидации UX-логики |

## В работе (in-progress)

_Пусто._

## Последние архивированные (для контекста)

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

| # | Вопрос | Влияние |
|---|---|---|
| Q1 | Что такое **T-098**? На него ссылаются T-127 и T-129 как depends_on, но тикета с таким ID нет ни в tickets/, ни в archive/. | Блокирует P0 demo-цепочку |
| Q2 | Что такое **T-047** и **T-131-ui** (depends_on у T-131)? | Блокирует T-131 (алерты) |
| Q3 | Что такое **T-094** (depends_on у T-126)? | Блокирует retrain XGBoost |
| Q4 | Нужно ли создавать недостающие тикеты или удалить ссылки? | Это Q1..Q3 — общий вопрос |

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

## Риски

| Риск | Вероятность | Импакт | Стратегия |
|---|---|---|---|
| Данные от организаторов в неожиданном формате | Средняя | Высокий | Гибкие парсеры в RealSource (T-026) + fallback стратегии |
| Максим №1 перегружен (Backend+ML) | Высокая | Высокий | Помощь от Максима №2 на API слое, Света — на валидации |
| Не успеваем GCN | Средняя | Низкий | COULD-фича (RICE < 5), есть fallback — XGBoost + Hybrid |
| Недостающие тикеты T-098/T-047/T-131-ui/T-094 (Q1..Q4) | Высокая | Средний | Либо создать, либо удалить ссылки — на следующей сессии |
