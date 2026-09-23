# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T11:55:00Z
> Обновлено: Cline после T-128 (capacity-aware load_pct)

## Цель

Завершить MVP для демо жюри: ✅ backend ETA + capacity-aware load_pct + frontend PassengerMode
готовы. Следующее — dispatcher alerts (T-131), URL routing (T-135), README fix (T-115).

## Git state

```
status: pending commit (T-127 changes uncommitted)
ahead of origin/master: +26 commits (после T-127 будет +3)
```

## Что сделано за последние сессии (8)

- **T-128** — capacity-aware load_pct (TRAM_CAPACITY, compute_load_pct, load_color, +22 теста) ✨ новый
- **T-127** — backend GET `/api/v1/predictions/eta?stop_id=X&n=3` (1h, 23 теста)
- T-129 — React/Vite режим «Пассажир» с ETA + load + рекомендация (1h, 35 tests)
- T-130 — recommend() pure function для passenger mode (1h, 97% test coverage)
- T-133 — слайд «Боли пассажиров → наше решение» (1h)
- T-042 — backend GET /api/v1/predictions/stop/{id}/route/{id} (3h)
- T-091 — fix mypy exclude regex (F-001)
- T-039 — ml benchmark scripts + api-gen scripts (5h)
- T-037 — ml reports/plots.py matplotlib headless Agg (3h)

## Архив (done за всё время): 36

## Что в работе

Пусто (T-127 только что завершён, готовы брать T-128 / T-115 / T-131 / T-135).

## Следующая задача

**T-131:** Алерты диспетчеру T-30 мин warning (RICE 8.10, 2h). Создаст
endpoint `/api/v1/insights/alerts?stop_id=X&window_min=30` который возвращает
список перегруженных остановок в ближайшие N минут.

Команда запуска:
```bash
cd apps/backend
uv run pytest tests/test_alerts.py -v  # tests пишем первыми (RED)
make api-gen && make fe-gen
```

> T-128 уже сделал `load_color()` (green/yellow/red/darkred) — T-131 переиспользует
> эту шкалу для определения «alert-worthy» stops (load_pct > 90% = warning).

## Открытые вопросы

- (нет)

## Артефакты на диске

### Backend (T-127) ✨ новые
- `apps/backend/app/forecast/load.py` — TRAM_CAPACITY (MappingProxyType), MAX_LOAD_PCT=150, compute_load_pct, load_color ✨ новый (124 строки)
- `apps/backend/app/api/predictions.py` — добавлен `@router.get("/predictions/eta")` (50 строк)
- `apps/backend/app/schemas/eta.py` — Pydantic `ETAPrediction` + `ETAResponse` (60 строк)
- `apps/backend/app/data/__init__.py` — пакет для domain helpers
- `apps/backend/app/data/transit.py` — `STOP_ROUTES`, `RouteRef`, `compute_eta_predictions`, `clamp_n` (220 строк)
- `apps/backend/tests/test_eta_endpoint.py` — 10 integration тестов (224 строки)
- `apps/backend/tests/test_eta_compute.py` — 15 unit-тестов (208 строк, +2 per-route capacity)
- `apps/backend/tests/test_compute_load_pct.py` — 20 unit-тестов capacity-aware (143 строки) ✨ новый
- `docs/hackathon/capacity_model.md` — модель вместимости трамваев Москвы (133 строки) ✨ новый

### Frontend (T-127) ✨ новые
- `apps/frontend/src/api/customInstance.ts` — fetch wrapper для Orval (F-011 fix)
- `apps/frontend/src/generated/api.ts` — обновлён, есть `useGetPredictionsEta` hook
- `apps/frontend/src/generated/api.schemas.ts` — `ETAPrediction`, `ETAResponse` TS типы

### Контракт (синхронизирован)
- `docs/api/openapi.json` — 8 paths, `ETAPrediction.predicted_load_pct` maximum повышен до 150.0 ✨ обновлён
- `apps/backend/app/schemas/eta.py` — `Field(le=100.0 → le=150.0)` для overload support
- `apps/frontend/src/lib/recommend.ts` — `ETAPrediction` TS интерфейс ↔ `apps/backend/app/schemas/eta.py` Pydantic (drop-in)

### Архив
- `docs/backlog/archive/T-127-backend-eta-endpoint-next-3-trams-with.md` — done, 8/8 AC ✓
- `docs/ledger/decisions.jsonl` — D-011 добавлено (STOP_ROUTES mock-match)
- `docs/ledger/findings.jsonl` — F-011 добавлено (отсутствовал customInstance.ts)
- `docs/backlog/STATUS.md` — 35 archive / 17 ready / 11 decisions / 11 findings

## Live verification (T-127)

```bash
$ curl -s 'http://127.0.0.1:8765/api/v1/predictions/eta?stop_id=1' | python3 -m json.tool
{
    "stop_id": 1,
    "generated_at": "2026-09-23T08:39:54.665647Z",
    "horizon_minutes": 60,
    "n_requested": 3,
    "trams": [
        {"route_id": 7,  "route_name": "7",  "eta_min": 10, "predicted_load_pct": 8.4, "model_id": "baseline_v1"},
        {"route_id": 9,  "route_name": "9",  "eta_min": 30, "predicted_load_pct": 8.4, "model_id": "baseline_v1"},
        {"route_id": 10, "route_name": "А", "eta_min": 50, "predicted_load_pct": 8.4, "model_id": "baseline_v1"}
    ]
}
```

## Последние решения в ledger

- **D-009**: Отказ от Streamlit UI → React/Vite (apps/frontend)
- **D-010**: nodeLinker=node-modules для apps/frontend (фикс EBADF под vitest@2)
- **D-012**: TRAM_CAPACITY в `forecast/load.py` (не `config.py`) — domain constant, not runtime ENV knob ✨ новый
- **D-011**: STOP_ROUTES hardcoded to match frontend mock (pixel-perfect demo)

## Последние находки

- **F-009**: TanStack Router plugin требует `src/routes/__root.tsx` → создан placeholder
- **F-010**: .prettierrc.json ссылается на отсутствующий `prettier-plugin-organize-imports` → убран из конфига
- **F-011**: apps/frontend/src/api/customInstance.ts отсутствовал → создан с поддержкой `params` для query-string ✨ новый

## Тестовые счётчики (после T-127)

| Модуль | Тестов | Coverage |
|---|---|---|
| apps/backend/tests/ | **73 passed** (было 51, +22 в T-128) | — |
| apps/frontend/src/ | **35 passed** (без изменений) | ~73% statements |
| ml/tests/ | (не запускались) | — |

## Не делать в следующей сессии

- ❌ Не патчить сгенерированные файлы в `apps/frontend/src/generated/`
- ❌ Не коммитить `.env`, `node_modules/`, `coverage/`, `.yarn/cache`, `dist/`
- ❌ Не использовать `npm install` или `pnpm install` (только yarn 4 + nodeLinker)
- ❌ Не читать `yarn.lock` / `uv.lock` в контекст
- ❌ Не пытаться переключить frontend обратно на Yarn 4 PnP (D-010 зафиксировал nodeLinker)
- ❌ Не добавлять `prettier-plugin-organize-imports` без надобности (F-010)
- ❌ Не удалять `src/routes/__root.tsx` — TanStack Router plugin требует его (F-009)
- ❌ Не удалять `apps/frontend/src/api/customInstance.ts` — Orval mutator (F-011)
- ❌ Не хардкодить STOP_ROUTES > 4 остановок без синхронного апдейта frontend mock (D-011)
- ❌ Не класть `TRAM_CAPACITY` в `config.py` — это domain constant, не ENV knob (D-012)
- ❌ Не менять `MAX_LOAD_PCT` без апдейта `schemas/eta.py::Field(le=...)` и `make api-gen`
- ❌ Не менять границы `load_color()` без обновления UI (recommend.ts)
