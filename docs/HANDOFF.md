# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T13:45:00Z
> Обновлено: Cline после T-135 (TanStack Router URL routing, DONE)

## Цель

Развивать frontend: после T-135 → **T-122 MapProvider** для визуальной части демо.
Реальные данные ~27.09 → retrain → submission checklist T-137. До этого — Track A: **T-122** (после T-135).

## Git state

```
status: uncommitted (T-135 changes pending commit)
branch: master
files changed (T-135, ~14 files, +400/-150):
  apps/frontend/src/App.tsx                                          (rewritten)
  apps/frontend/src/App.test.tsx                                     (rewritten, 2 tests)
  apps/frontend/src/routes/__root.tsx                                (expanded: header + Outlet)
  apps/frontend/src/routes/{index,passenger,dispatcher,analyst,planner}.tsx  (5 new)
  apps/frontend/src/routes/-__root.test.tsx                          (new, 6 tests)
  apps/frontend/src/routeTree.gen.ts                                 (auto-regen, 200 lines)
  apps/frontend/src/components/Layout/RoleSwitcherNav.tsx            (new)
  apps/frontend/src/components/Layout/PlaceholderPanel.tsx           (new)
  apps/frontend/src/lib/roles.ts                                     (new, pure data)
  apps/frontend/src/test/setup.ts                                    (jsdom scrollTo fix, F-014)
  apps/frontend/src/lib/i18n/t.test.ts                               (eslint-disable fix)
  docs/backlog/STATUS.md                                             (counters updated)
  docs/ledger/findings.jsonl                                         (F-014 appended)
```

## Что сделано за последние сессии (12)

- **T-135** — TanStack Router URL routing DONE — 5 file-based маршрутов, `<RouterProvider>` module-level singleton, `<Link>` nav в header, `defaultPreload: 'intent'`, type-safe `<Link to="...">` через Register interface, 6+2 новых тестов, **60/60 frontend зелёные**, build 1.29s. F-014 зафиксирован. ✨ новый
- **T-141** — frontend text registry hybrid t(key) DONE (предыдущая сессия)
- **D-014** — Hybrid text registry решение (RICE ~6) — записано в ledger
- **T-115** — скорректирован: убран English README, добавлена ссылка на T-141

## Что сделано за предыдущие сессии (10)

- **T-131** — dispatcher overload alerts (`/api/v1/insights/alerts` + React AlertsPanel, 21+3 теста)
- T-128 — capacity-aware load_pct (TRAM_CAPACITY, compute_load_pct, load_color, +22 теста)
- T-127 — backend GET `/api/v1/predictions/eta?stop_id=X&n=3` (1h, 23 теста)
- T-129 — React/Vite режим «Пассажир» с ETA + load + рекомендация (1h, 35 tests)
- T-130 — recommend() pure function для passenger mode (1h, 97% test coverage)
- T-133 — слайд «Боли пассажиров → наше решение» (1h)
- T-042 — backend GET /api/v1/predictions/stop/{id}/route/{id} (3h)
- T-091 — fix mypy exclude regex (F-001)
- T-039 — ml benchmark scripts + api-gen scripts (5h)
- T-037 — ml reports/plots.py matplotlib headless Agg (3h)

## Архив (done за всё время): **39** (+T-135)

## Что в работе

Пусто (T-135 DONE, готовы брать **T-122** / T-115 / T-137 / T-125).

## Следующая задача

**Track A — frontend визуальная часть**:
- **T-122 (P1, RICE 2.70, 4h, baev)** — MapProvider + LeafletMap + YandexMap. **Следующая цель после T-135**. Нужно решить: визуальная карта критична для демо жюри или достаточно текстовой версии (passenger mode показывает stop list + ETA)?

Команда запуска T-122:
```bash
cat docs/backlog/tickets/T-122-*.md
$EDITOR apps/frontend/src/components/Map/MapProvider.tsx
yarn --cwd apps/frontend test:run
```

**Track B (после 27.09 real data)**:
- **T-137 (P0, RICE 6.00, 2h)** — docs/HACKATHON_CHECKLIST.md R8 submission
- **T-115 (P1, RICE 10.00, 1h)** — README Russian + Handover
- **T-125 (P2, RICE 5.40, 2h)** — feature engineering: weather + traffic

## Открытые вопросы

- **T-122 — визуальная карта vs текст?** Если жюри не критично — отложить до post-hackathon. Если критично — брать сейчас.
- **F-014 (NEW)**: jsdom scrollTo warning. Подавлено для 8/9 тестов через `Object.defineProperty`. Один остаточный warning в `-__root.test.tsx > /passenger` (createMemoryHistory triggers scrollTo до setup). Не блокер; оставлено как есть.

## Артефакты на диске

### Frontend (T-135) ✨ новые
- `apps/frontend/src/routes/__root.tsx` — root layout: header + nav + `<Outlet/>`, `useRouterState` для active role ✨
- `apps/frontend/src/routes/{index,passenger,dispatcher,analyst,planner}.tsx` — 5 file-based маршрутов ✨
- `apps/frontend/src/routes/-__root.test.tsx` — 6 vitest тестов (префикс `-` чтобы router plugin не сканировал) ✨
- `apps/frontend/src/routeTree.gen.ts` — авто-регенерирован vite plugin (200 строк) ✨
- `apps/frontend/src/components/Layout/RoleSwitcherNav.tsx` — `<Link>`-based nav ✨
- `apps/frontend/src/components/Layout/PlaceholderPanel.tsx` — placeholder для analyst/planner ✨
- `apps/frontend/src/lib/roles.ts` — pure data: ROLES, RoleDef, roleFromPathname ✨
- `apps/frontend/src/App.tsx` — module-level `<RouterProvider>` singleton + Register interface ✨
- `apps/frontend/src/test/setup.ts` — F-014: Object.defineProperty для scrollTo ✨
- `apps/frontend/src/lib/i18n/t.test.ts` — фикс unused eslint-disable ✨

### Frontend skeleton (T-141, без изменений в этой сессии)
- `apps/frontend/src/lib/i18n/{ru-RU,keys,t}.ts` — text registry
- `apps/frontend/src/components/Dispatcher/{AlertsPanel,AlertCard}.tsx`
- `apps/frontend/src/pages/PassengerMode.tsx`
- `apps/frontend/src/lib/{recommend,EtaCard,Alert,loadTier,etaClient}.ts`
- `Makefile` — `lint-frontend-text` + `frontend-text-check` (CI gate для D-014)

### Backend (T-131) (без изменений в этой сессии)
- `apps/backend/app/insights/__init__.py` — пакет ✨ новый
- `apps/backend/app/insights/alerts.py` — OverloadAlert dataclass + find_overload_alerts + classify_load + SEVERITY_* + MAX_LOAD_PCT re-export ✨ новый (135 строк)
- `apps/backend/app/api/alerts.py` — GET /api/v1/insights/alerts?window_min=N router ✨ новый (118 строк)
- `apps/backend/app/schemas/alerts.py` — OverloadAlert + OverloadAlertsResponse Pydantic ✨ новый (90 строк)
- `apps/backend/app/main.py` — зарегистрирован alerts_router
- `apps/backend/tests/test_find_overload_alerts.py` — 16 unit-тестов ✨ новый
- `apps/backend/tests/test_alerts_endpoint.py` — 5 integration тестов ✨ новый

### Frontend (T-131) ✨ новые
- `apps/frontend/src/components/Dispatcher/AlertsPanel.tsx` — useQuery + refetchInterval(60s) ✨ новый
- `apps/frontend/src/components/Dispatcher/AlertCard.tsx` — карточка с severity pill ✨ новый
- `apps/frontend/src/components/Dispatcher/AlertCard.test.tsx` — 3 vitest кейса ✨ новый
- `apps/frontend/src/App.tsx` — role='dispatcher' → <AlertsPanel /> (вместо PlaceholderPanel)
- `apps/frontend/src/App.test.tsx` — обёрнут в QueryClientProvider

### Контракт (синхронизирован)
- `docs/api/openapi.json` — 9 paths (+/api/v1/insights/alerts)
- `apps/frontend/src/generated/api.ts` — hook `useGetOverloadAlertsApiV1InsightsAlertsGet` ✨ новый
- `apps/frontend/src/generated/api.schemas.ts` — `OverloadAlert`, `OverloadAlertsResponse`

### Архив
- `docs/backlog/archive/T-131-dispatcher-alerts-overload-predictions-15.md` — done, 8/8 AC ✓
- `docs/ledger/decisions.jsonl` — D-013 (setInterval + /insights/alerts URL rationale)
- `docs/backlog/STATUS.md` — 37 archive / 23 ready / 13 decisions / 11 findings

### Gap-analysis (готовые к старту, топ-5) ✨
- `docs/backlog/tickets/T-122-...md` — MapProvider + LeafletMap + YandexMap (P1, RICE 2.70, 4h, baev) — **следующая цель**
- `docs/backlog/tickets/T-115-...md` — README Russian + Handover (P1, RICE 10.00, 1h)
- `docs/backlog/tickets/T-125-...md` — feature engineering: weather + traffic (P2, RICE 5.40, 2h, maxim)
- `docs/backlog/tickets/T-134-...md` — backend /predictions/route/{id}?horizon=month (P1, RICE 1.40, maxim)
- `docs/backlog/tickets/T-136-...md` — backend /predictions/route/{id}?horizon=year + Monte Carlo (P1, RICE 1.20, maxim)
- `docs/backlog/tickets/T-137-...md` — docs/HACKATHON_CHECKLIST.md R8 (P0, RICE 6.00, 2h, maxim+svetlana)
- `docs/backlog/tickets/T-138-...md` — apps/assistant LiteLLM skeleton (P2, RICE 1.50, maxim)
- `docs/backlog/tickets/T-139-...md` — apps/mcp stdio JSON-RPC server (P2, RICE 1.60, maxim)
- `docs/backlog/tickets/T-140-...md` — ml GCN+LSTM spatiotemporal (P2, RICE 0.60, unassigned)
- `docs/backlog/archive/T-135-...md` — TanStack Router URL routing (DONE) ✨
- `docs/backlog/archive/T-141-...md` — text registry hybrid t(key) (DONE)
- `.clinerules/20-text-constants-registry.md` — clinerule для text registry
- `docs/ledger/decisions.jsonl` — D-014 (hybrid t(key) без react-i18next) ✨ новый

## Live verification (T-135)

```bash
$ yarn --cwd apps/frontend typecheck   # 0 errors
$ yarn --cwd apps/frontend lint        # ESLint clean + Prettier clean
$ yarn --cwd apps/frontend test:run    # 60/60 passed (9 test files)
$ yarn --cwd apps/frontend build       # 200 modules, 1.29s
$ make frontend-text-check             # ✓ No hardcoded UI strings
```

Coverage:
- All files: 90.75% stmts, 79.11% branch, 90.9% funcs
- `src/routes/`: 100% stmts, 86.66% branch
- `src/lib/roles.ts`: 95% (непокрыты только error-throw ветки)

## Последние решения в ledger

- **D-014**: Hybrid text registry `t(key)` без `react-i18next` на хакатоне (RICE ~6)
- **D-013**: Dispatcher alerts polling — setInterval через TanStack Query
- **D-012**: TRAM_CAPACITY в `forecast/load.py`
- **D-011**: STOP_ROUTES hardcoded to match frontend mock
- **D-010**: nodeLinker=node-modules для apps/frontend

## Тестовые счётчики (после T-135)

| Модуль | Тестов | Coverage |
|---|---|---|
| apps/backend/tests/ | **94 passed** | — |
| apps/frontend/src/ | **60 passed** (было 55, +5 нетто новых в T-135) | 90.75% statements |
| ml/tests/ | (не запускались в этой сессии) | — |

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
- ❌ Не добавлять `streamlit-autorefresh` или другие Streamlit-пакеты (D-013)
- ❌ Не менять URL `/api/v1/insights/alerts` на `/api/v1/alerts/overload` (D-013)
- ❌ Не создавать README.en.md — хакатон русский, English не нужен (T-115 scope-down)
- ❌ Не хардкодить русские/UI строки в .tsx вне `apps/frontend/src/lib/i18n/` (D-014, T-141)
- ❌ Не использовать `cd apps/frontend && yarn ...` chains в multi-command tool calls — `yarn --cwd <abs-path>` обязательно (F-013)
- ❌ Не удалять/изменять `Makefile` `lint-frontend-text` — CI gate для D-014
- ❌ Не класть `RoleSwitcherNav`/`PlaceholderPanel` в `apps/frontend/src/routes/` — TanStack Router plugin попытается сделать из них маршруты; они живут в `components/Layout/`
- ❌ Не использовать `!` non-null assertions в `.ts/.tsx` — `@typescript-eslint/no-non-null-assertion` запрещает; использовать runtime guards с `throw new Error()`
- ❌ Не забывать `await router.load()` в vitest-тестах с `createMemoryHistory` перед `render(<RouterProvider>)` (TanStack Router v1.x async navigation)
- ❌ Не забывать оборачивать тесты `<RoleSwitcherNav>` в `<RouterProvider>` — `<Link>` требует router context (или падает с `Cannot read properties of null (reading 'isServer')`)
- ❌ Не добавлять тестовые файлы в `routes/` без префикса `-` (router plugin warning); vitest при этом всё равно их найдёт через паттерн `*.test.tsx`
- ❌ Не использовать `time_to_overload_min` с одинаковой семантикой для всего stop — каждая карточка = свой трамвай (D-013)
