---
id: T-218
phase: 4
title: PassengerMode переключить на predictions (не actuals)
priority: P0
effort: 4
unit: hours
rice:
  R: 4
  I: 3
  C: 0.9
  score: 2.7
depends_on: []
blocks: []
tags: [frontend, backend, predictions, clinerule-31, post-hackathon-debt]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

В dev/demo режиме пассажирский экран показывает «нет данных» по всем 9 маршрутам, потому что фронт берёт данные из `/api/v1/historical/{id}?granularity=hour` (actuals), а backend вычисляет окно как «последние 7 дней от now()`. Реальное `now()` (2026-09-27) за пределами датасета (заканчивается 2025-10-31), окно пустое → «нет данных».

Принято решение (по запросу пользователя 2026-09-27, уточнение в act-mode):
**PassengerMode показывает два блока рядом** — «как было» (actuals) + «как будет» (predictions), чтобы пассажир мог сравнить и выбрать свободный маршрут.

Actuals блок берётся из БД с **fallback на MAX(period_start)** (не `now()`), чтобы окно не было пустым. Predictions блок берётся за submission period (`2025-11-01..2025-12-31`).

## Source contract (clinerule 31)

| Экран | Источник | Эндпоинт |
|---|---|---|
| PassengerMode (нагрузка по линиям) | **Predictions** | `GET /api/v1/predictions/load` |
| AnalystDashboard (historical chart) | Actuals | `GET /api/v1/historical/{id}` |
| AnalystDashboard (predictions chart) | Predictions | `GET /api/v1/predictions/db/{id}` |
| AlertsPanel | Predictions (overload) | `GET /api/v1/insights/alerts` |

`/api/v1/predictions/load` — новый summary endpoint (по одному на все маршруты):
- `from_date`, `to_date` опциональны (default = `2025-11-01..2025-12-31` = submission period)
- `model_id`, `feature_set`, `zeros_applied` опциональны (= best/F-083)
- Возвращает `[{route_id, boardings_avg, load_pct, tier}]` для всех маршрутов с непустыми predictions
- `load_pct = boardings_avg / TRAM_CAPACITY × 100`

## Acceptance Criteria

**Backend:**
- [ ] `apps/backend/app/load_tier.py` — пороги tier (green/yellow/red/darkred) + тесты
- [ ] `GET /api/v1/historical/load` — summary actuals (avg per route за последний доступный день)
- [ ] `GET /api/v1/predictions/load` — summary predictions (avg per route за submission period)
- [ ] `_resolve_history_window` fallback: если окно пустое → `[MAX(period_start) - 7d, MAX(period_start)]`
- [ ] Backend тесты: `test_api_t218.py` (predictions) + `test_historical_load.py` (actuals) + `test_load_tier.py`
- [ ] OpenAPI свежий (`make api-gen` без ошибок)

**Frontend:**
- [ ] `apps/frontend/src/lib/routeLoad.ts`: `fetchActualsLoad()` + `fetchPredictionsLoad()`
- [ ] `apps/frontend/src/pages/PassengerMode.tsx`: два блока (`actuals-grid` + `predictions-grid`)
- [ ] `apps/frontend/src/components/Passenger/RouteLoadCard.tsx`: опциональный `variant: actual|prediction` (подписи «было»/«будет»)
- [ ] i18n: `passenger.actualsHeader`, `passenger.predictionsHeader`, `passenger.actualBadge`, `passenger.predictionBadge`
- [ ] vitest тесты зелёные (обновить моки)
- [ ] Live: в браузере `/passenger` оба блока показывают tier≠unknown с реальными числами

**Knowledge / docs:**
- [ ] Clinerule: `.clinerules/31-passenger-mode-actuals-and-predictions.md` создан + индекс обновлён
- [ ] Ledger: F-NNN (time-drift) + D-NNN (two-block passenger)
- [ ] HANDOFF: `docs/HANDOFF.md` обновлён с описанием T-218

## Technical Notes

**Backend (1 новый endpoint):**

```python
# apps/backend/app/api/predictions_load.py (новый)
@router.get("/predictions/load", response_model=RouteLoadListResponse)
async def get_route_loads(...):
    # SELECT route_id, AVG(value) FROM predictions WHERE period_start IN [from..to]
    # GROUP BY route_id → boardings_avg
    # load_pct = boardings_avg / TRAM_CAPACITY × 100
    # tier = loadTier(load_pct) из ml.transit_ai.frontend (или share constant)
```

**Frontend:**
- `fetchAllRouteLoads()` → `GET /api/v1/predictions/load` (вместо Promise.all по route_id)
- `fetchRoutesList()` → больше не нужен (summary endpoint возвращает все маршруты)
- Удалить `fetchRoutesList` если он нигде больше не используется

**Tier computation:**
- Вместо вызова `loadTier()` в backend (он в TypeScript), перенести логику в Python или использовать простые пороги: green<70, yellow<90, red<110, darkred>=110 (как в `apps/frontend/src/lib/loadTier.ts`).
- Альтернатива: backend возвращает только `load_pct`, frontend сам считает `tier` через существующий `loadTier()`.

**TRAM_CAPACITY** — 150 (default в `apps/frontend/src/lib/routeLoad.ts:20`).

## Verification

```bash
# 1. Backend live
curl -sS http://localhost:8000/api/v1/predictions/load | python3 -m json.tool
# Должен вернуть [{route_id: 1, boardings_avg: ..., load_pct: ..., tier: ...}, ...]

# 2. Frontend build
cd apps/frontend && yarn build

# 3. Browse
open http://localhost:5173/passenger
# 9 карточек маршрутов с цветной tier (не серые «нет данных»)

# 4. Tests
uv run pytest apps/backend/tests/test_api_t218.py -v
cd apps/frontend && yarn test:run apps/frontend/src/lib/routeLoad.test.ts
make check-all
```

## Status

`in-progress` (2026-09-27, после Act mode)
## Verified

- Backend: 28 passed (5 load_tier + 3 historical_load + 3 predictions_load + 17 existing t195)
- Frontend: 110/110 vitest passed
- Typecheck: 0 errors
- Live: `curl localhost:8000/api/v1/predictions/load` → 9 route_ids; `curl localhost:8000/api/v1/historical/load` → 9 route_ids с fallback `used_fallback=true` (MAX period 2025-10-24..2025-10-31)
- OpenAPI regen: 22 paths (было 20, +2 новых /historical/load и /predictions/load)
- Orval regen: `getHistoricalLoadApiV1HistoricalLoadGet` + `getPredictionsLoadApiV1PredictionsLoadGet` в `apps/frontend/src/generated/api.ts`
- Clinerule: `.clinerules/31-passenger-mode-actuals-and-predictions.md` создан, индекс `00-AGENTS.md` обновлён
- Ledger: F-096 + D-036
