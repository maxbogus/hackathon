# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T08:45:00Z
> Обновлено: Cline после T-127 (Backend ETA endpoint)

## Цель

Завершить MVP для демо жюри: ✅ backend ETA + frontend PassengerMode готовы. Следующее —
capacity-aware load_pct (T-128) и dispatcher alerts (T-131).

## Git state

```
status: pending commit (T-127 changes uncommitted)
ahead of origin/master: +26 commits (после T-127 будет +3)
```

## Что сделано за последние сессии (8)

- **T-127** — backend GET `/api/v1/predictions/eta?stop_id=X&n=3` (1h, 23 теста) ✨ новый
- T-129 — React/Vite режим «Пассажир» с ETA + load + рекомендация (1h, 35 tests)
- T-130 — recommend() pure function для passenger mode (1h, 97% test coverage)
- T-133 — слайд «Боли пассажиров → наше решение» (1h)
- T-042 — backend GET /api/v1/predictions/stop/{id}/route/{id} (3h)
- T-091 — fix mypy exclude regex (F-001)
- T-039 — ml benchmark scripts + api-gen scripts (5h)
- T-037 — ml reports/plots.py matplotlib headless Agg (3h)

## Архив (done за всё время): 35

## Что в работе

Пусто (T-127 только что завершён, готовы брать T-128 / T-115 / T-131 / T-135).

## Следующая задача

**T-128:** `load_pct` прогноз с учётом capacity трамвая — per-route tram capacity
(Витязь 150-200, Львёнок 100), чтобы load_pct стал реалистичным. Заменит
`DEFAULT_TRAM_CAPACITY = 150` хардкод.

Команда запуска:
```bash
cd apps/backend
uv run pytest tests/test_eta_compute.py -v
make api-gen && make fe-gen
```

> T-127 уже добавил структуру для per-route capacity (RouteRef dataclass + STOP_ROUTES
> dict). T-128 расширит её per-route атрибутом `capacity_pax` и обновит compute_eta_predictions
> чтобы использовать capacity из маршрута, а не global default.

## Открытые вопросы

- (нет)

## Артефакты на диске

### Backend (T-127) ✨ новые
- `apps/backend/app/api/predictions.py` — добавлен `@router.get("/predictions/eta")` (50 строк)
- `apps/backend/app/schemas/eta.py` — Pydantic `ETAPrediction` + `ETAResponse` (60 строк)
- `apps/backend/app/data/__init__.py` — пакет для domain helpers
- `apps/backend/app/data/transit.py` — `STOP_ROUTES`, `RouteRef`, `compute_eta_predictions`, `clamp_n` (220 строк)
- `apps/backend/tests/test_eta_endpoint.py` — 10 integration тестов (224 строки)
- `apps/backend/tests/test_eta_compute.py` — 13 unit-тестов pure functions (182 строки)

### Frontend (T-127) ✨ новые
- `apps/frontend/src/api/customInstance.ts` — fetch wrapper для Orval (F-011 fix)
- `apps/frontend/src/generated/api.ts` — обновлён, есть `useGetPredictionsEta` hook
- `apps/frontend/src/generated/api.schemas.ts` — `ETAPrediction`, `ETAResponse` TS типы

### Контракт (синхронизирован)
- `docs/api/openapi.json` — 8 paths (было 7), `ETAResponse` schema добавлена
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
- **D-011**: STOP_ROUTES hardcoded to match frontend mock (pixel-perfect demo) ✨ новый

## Последние находки

- **F-009**: TanStack Router plugin требует `src/routes/__root.tsx` → создан placeholder
- **F-010**: .prettierrc.json ссылается на отсутствующий `prettier-plugin-organize-imports` → убран из конфига
- **F-011**: apps/frontend/src/api/customInstance.ts отсутствовал → создан с поддержкой `params` для query-string ✨ новый

## Тестовые счётчики (после T-127)

| Модуль | Тестов | Coverage |
|---|---|---|
| apps/backend/tests/ | **51 passed** (было 28, +23) | — |
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
