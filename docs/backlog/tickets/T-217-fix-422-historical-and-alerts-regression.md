---
id: T-217
phase: 7
title: Fix 422 regression on /historical/{id} and /insights/alerts
priority: P0
effort: 3
unit: hours
rice:
  R: 10
  I: 3
  C: 1.0
  score: 10.0
depends_on: []
blocks: [T-200, T-201]
tags: [regression, api-contract, frontend, ml, ui-bug, openapi, orval, hackathon]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

F-097: После T-200 (HorizonToggle с кнопками 1d/3m/1y) и обновления routeLoad.ts
(PassengerMode агрегирует по маршруту) в браузерной консоли жюри появились
16 ошибок 422 на критические эндпоинты:

- 10× `GET /api/v1/historical/{1,7,11,12,17,25,26,28,50}?granularity=hour` →
  `422 missing query params: from, to` (PassengerMode routeLoad не передавал
  диапазон дат, а backend делал их `Query(...)` обязательными).
- 6× `GET /api/v1/insights/alerts?window_min={1440|131400|525600}` →
  `422 Input should be less than or equal to 120` (HorizonToggle слал
  «минуты» для горизонтов «день/месяц/год», но backend ограничивал
  `MAX_WINDOW_MIN=120` для dispatcher look-ahead).

Это блокировало Целевые задачи ТЗ:

- **Задача 1** (прогноз на 3 горизонта) — UI есть, backend не отвечает 200.
- **Задача 2** (агрегация по маршруту) — 10/10 маршрутов падают.
- **Задача 3** (исторические данные → UI) — поток разорван на последнем метре.

## Acceptance Criteria

- [x] `GET /api/v1/historical/{id}?granularity=hour` (без from/to) → 200,
      default = последние 7 дней.
- [x] `GET /api/v1/historical/{id}?from=...` (только from) → 200,
      to = from + 7 дней.
- [x] `GET /api/v1/historical/{id}?to=...` (только to) → 200,
      from = to - 7 дней.
- [x] `GET /api/v1/insights/alerts?window_min=1440` → 200 (≤1440).
- [x] `GET /api/v1/insights/alerts?window_min=5000` → 422 (>1440).
- [x] `GET /api/v1/insights/alerts?horizon=day` → 200, body содержит `horizon: "day"`.
- [x] `GET /api/v1/insights/alerts?horizon=month|year` → 200 (Целевая задача 1).
- [x] `GET /api/v1/insights/alerts?horizon=week` → 422 (pattern mismatch).
- [x] OpenAPI регенерирован: `docs/api/openapi.json` отражает optional from/to + horizon.
- [x] Orval регенерирован: `apps/frontend/src/generated/api.ts` содержит
      `horizon?: string` и `from?: string | null`.
- [x] Frontend: `HorizonToggle.tsx` экспортирует `apiHorizonFor(key) = 'day'|'month'|'year'`.
- [x] Frontend: `AlertsPanel.tsx` передаёт `{horizon: apiHorizonFor(horizon)}` (не window_min).
- [x] Backend tests: pytest 41 passed (3 новых теста на optional from/to + horizon param).
- [x] Backend lint: ruff passes на моих файлах.
- [x] Backend mypy: passes на моих файлах.
- [x] Frontend typecheck: passes (down с 7 pre-existing до 0 моих).
- [x] Frontend vitest: 99 → 110 passed (+11).
- [x] Ledger: F-097 (находка) + D-036 (решение horizon param).

## Technical Notes

### Backend fix #1: `/api/v1/historical/{route_id}`

`apps/backend/app/api/historical.py`:
- Сделал `from_date: datetime | None` и `to_date: datetime | None` с default `None`.
- Добавил `_resolve_history_window()` (helper): если оба None → последние 7 дней;
  если только from → to = from + 7д; если только to → from = to - 7д.

### Backend fix #2: `/api/v1/insights/alerts`

`apps/backend/app/insights/alerts.py`:
- Поднял `MAX_WINDOW_MIN` 120 → 1440 (1 день).
- Добавил `HORIZONS = ('day', 'month', 'year')`, `DEFAULT_HORIZON = 'day'`,
  `HORIZON_ETA_COUNT = {'day': 5, 'month': 30, 'year': 60}`.

`apps/backend/app/api/alerts.py`:
- Добавил query param `horizon: str = Query('day', pattern='^(day|month|year)$')`.
- В `_eta_by_stop(..., n)` использую `n=HORIZON_ETA_COUNT[horizon]`.
- В `OverloadAlertsResponse` добавил поле `horizon: str`.

### Frontend fix: contract-first flow

1. `make api-gen` → `docs/api/openapi.json` (новые optional params + horizon).
2. `make fe-gen` → `apps/frontend/src/generated/api.ts` (Orval).
3. `apps/frontend/src/components/Dispatcher/HorizonToggle.tsx`:
   - Экспортирует `apiHorizonFor(key): 'day'|'month'|'year'`.
   - Старый `windowMinFor(key)` удалён (был хардкод минут).
4. `apps/frontend/src/components/Dispatcher/AlertsPanel.tsx`:
   - Передаёт `{horizon: apiHorizonFor(horizon)}` (не `window_min`).
   - `data.horizon` отображается через `dispatcher.alerts.horizonSuffix`.

### Bonus fix: `customInstance.ts`

`apps/frontend/src/api/customInstance.ts`:
- F-095 follow-up: мутор возвращал `CustomResponse<T>`, но Orval хуки
  ожидают `T` (развёрнутый). Раньше работало, потому что другие компоненты
  тянули `response.data.X`. С моими regenerations стало типизированно — TS
  начал падать на `data.alerts` (5+ ошибок в AlertsPanel).
- **Breaking change**: мутор теперь возвращает `Promise<T>`.
- Headers/status остаются через `lastResponse()` singleton helper
  (для `downloadCsv.ts` которому нужен X-Row-Count, X-CSV-MD5).
- Расширил тип `params?: Record<string, ...|null|undefined>` чтобы Orval
  хуки с `from?: string | null` компилировались.

Также добавил pre-existing i18n ключ `passenger.routesEmpty` (использовался в `PassengerMode.tsx` но отсутствовал в `ru-RU.ts`) → фиксит ещё 1 typecheck ошибку.

## Verification

```bash
# Backend
cd apps/backend && uv run pytest tests/test_alerts_endpoint.py tests/test_api_t195.py tests/test_find_overload_alerts.py -v --no-cov
# → 41 passed

# Backend live (uvicorn local)
curl "http://localhost:8000/api/v1/historical/1?granularity=hour"  # → HTTP 200
curl "http://localhost:8000/api/v1/insights/alerts?horizon=year"   # → HTTP 200
curl "http://localhost:8000/api/v1/insights/alerts?horizon=week"   # → HTTP 422

# Frontend
cd apps/frontend && yarn typecheck  # → 0 errors
cd apps/frontend && yarn test:run   # → 110 passed
```

## Status

done (закоммичено одной серией, см. Conventional Commits)
