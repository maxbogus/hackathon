# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T13:40:00Z
> Обновлено: Cline после T-141 (text registry hybrid t(key), DONE)

## Цель

Развивать frontend с text-registry + картой; backend готов (ETA + capacity + alerts).
Реальные данные ~27.09 → retrain → submission checklist T-137. До этого — Track A: **T-135 → T-122** (URL routing + map).

## Git state

```
status: clean
latest commit: 61524a3 feat(frontend): hybrid text registry t(key) — migrate 5 UI files (T-141)
new commits since T-131: 6
  4930f07 chore(backlog): add text registry rule + T-141 hybrid t(key), scope-down T-115
  61524a3 feat(frontend): hybrid text registry t(key) — migrate 5 UI files (T-141)
ahead of origin/master: +37 commits
```

## Что сделано за последние сессии (11)

- **T-141** — frontend text registry hybrid t(key) DONE — 40+ ключей в `lib/i18n/`, 5 файлов мигрированы (App.tsx, AlertsPanel, AlertCard, PassengerMode, EtaCard), `make frontend-text-check` gate, типобезопасность через `TKey = Leaves<typeof TEXTS>`. Tests: 17/17 i18n + 55/55 total. Yarn build: green. ✨ новый
- **D-014** — Hybrid text registry решение (RICE ~6) — записано в ledger (см. session earlier)
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

## Архив (done за всё время): 37 (unchanged this session)

## Что в работе

Пусто (T-141 DONE, готовы брать T-115 / T-135 / T-137 / T-125).

## Следующая задача

**Track A — frontend refactor** (T-141 → T-135 → T-122). После T-141 **unblocked**:
- **T-135 (P1, RICE 6.00, 2h, baev)** — TanStack Router URL routing для role-switcher. Route names теперь могут идти через `t()`.
- **T-122 (P1, RICE 2.70, 4h, baev)** — MapProvider + LeafletMap + YandexMap (нужно для визуальной части демо жюри).
- **T-125 (P2, RICE 5.40, 2h, maxim)** — weather + traffic фичи (можно параллельно с Track A).

> **Track B (после 27.09 real data)**: T-137 (R8 checklist) → T-115 (README) → T-039 (re-train benchmark).

Команда запуска T-135:
```bash
cat docs/backlog/tickets/T-135-*.md
$EDITOR apps/frontend/src/routes/__root.tsx   # convert useState to Link/useNavigate
yarn --cwd apps/frontend test:run
```

## Открытые вопросы

- T-122 RICE mismatch (был 4.5 в YAML, формула даёт 2.70) — починен, записано как F-012.
- F-013 (NEW): yarn cwd issue в multi-command tool calls — использовать `yarn --cwd <abs-path>` (см. findings F-013 ниже).

## Артефакты на диске

### Frontend (T-141) ✨ новые
- `apps/frontend/src/lib/i18n/ru-RU.ts` — типизированный словарь 40+ ключей ✨
- `apps/frontend/src/lib/i18n/keys.ts` — рекурсивный `TKey = Leaves<typeof TEXTS>` ✨
- `apps/frontend/src/lib/i18n/t.ts` — `t(key)` + `tf(key, ...args)` ✨
- `apps/frontend/src/lib/i18n/t.test.ts` — 17 unit тестов + 1 snapshot ✨
- `apps/frontend/src/lib/i18n/MIGRATION.md` — лог миграций ✨
- `apps/frontend/src/App.tsx` — мигрирован (Role table → label/description/placeholder keys) ✨
- `apps/frontend/src/components/Dispatcher/{AlertsPanel,AlertCard}.tsx` — мигрированы ✨
- `apps/frontend/src/pages/PassengerMode.tsx` — мигрирован (`recommend.text` остаётся pure-data) ✨
- `apps/frontend/src/lib/EtaCard.tsx` — мигрирован ✨
- `Makefile` — добавлены `lint-frontend-text` + `frontend-text-check`; обе `check-all` цепочки обновлены ✨

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

### Gap-analysis (new in this session) ✨
- `docs/backlog/tickets/T-122-...md` — MapProvider + LeafletMap + YandexMap (P1, RICE 2.70, baev)
- `docs/backlog/tickets/T-134-...md` — backend /predictions/route/{id}?horizon=month (P1, RICE 1.40, maxim)
- `docs/backlog/tickets/T-135-...md` — TanStack Router URL routing (P1, RICE 6.00, baev) [hotfix: title quoted]
- `docs/backlog/tickets/T-136-...md` — backend /predictions/route/{id}?horizon=year + Monte Carlo (P1, RICE 1.20, maxim)
- `docs/backlog/tickets/T-137-...md` — docs/HACKATHON_CHECKLIST.md R8 (P0, RICE 6.00, maxim+svetlana)
- `docs/backlog/tickets/T-138-...md` — apps/assistant LiteLLM skeleton (P2, RICE 1.50, maxim)
- `docs/backlog/tickets/T-139-...md` — apps/mcp stdio JSON-RPC server (P2, RICE 1.60, maxim)
- `docs/backlog/tickets/T-140-...md` — ml GCN+LSTM spatiotemporal (P2, RICE 0.60, unassigned)
- `docs/backlog/tickets/T-141-...md` — frontend text registry hybrid t(key) (P1, RICE 1.20, baev) ✨ новый
- `.clinerules/20-text-constants-registry.md` — clinerule для text registry ✨ новый
- `docs/ledger/decisions.jsonl` — D-014 (hybrid t(key) без react-i18next) ✨ новый

## Live verification (T-131)

```bash
# через TestClient (backend не запущен в этой сессии)
$ pytest apps/backend/tests/test_alerts_endpoint.py -v
tests/test_alerts_endpoint.py::test_alerts_route_returns_200_with_default_window PASSED
tests/test_alerts_endpoint.py::test_alerts_route_accepts_window_min_query PASSED
tests/test_alerts_endpoint.py::test_alerts_route_rejects_negative_window_min PASSED
tests/test_alerts_endpoint.py::test_alerts_route_rejects_overlong_window_min PASSED
tests/test_alerts_endpoint.py::test_alerts_payload_alert_shape_when_present PASSED
```

## Последние решения в ledger

- **D-014**: Hybrid text registry `t(key)` без `react-i18next` на хакатоне ✨ новый
- **D-013**: Dispatcher alerts polling — setInterval через TanStack Query (не streamlit-autorefresh), URL /api/v1/insights/alerts (не /alerts/overload)
- **D-012**: TRAM_CAPACITY в `forecast/load.py` (не `config.py`) — domain constant, not runtime ENV knob
- **D-011**: STOP_ROUTES hardcoded to match frontend mock (pixel-perfect demo)
- **D-010**: nodeLinker=node-modules для apps/frontend (фикс EBADF под vitest@2)

## Тестовые счётчики (после T-131)

| Модуль | Тестов | Coverage |
|---|---|---|
| apps/backend/tests/ | **94 passed** (было 73, +21 в T-131) | — |
| apps/frontend/src/ | **38 passed** (было 35, +3 в T-131) | ~73% statements |
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
- ❌ Не добавлять `streamlit-autorefresh` или другие Streamlit-пакеты (D-013)
- ❌ Не менять URL `/api/v1/insights/alerts` на `/api/v1/alerts/overload` (D-013)
- ❌ Не создавать README.en.md — хакатон русский, English не нужен (T-115 scope-down)
- ❌ Не хардкодить русские/UI строки в .tsx вне `apps/frontend/src/lib/i18n/` (D-014, T-141)
- ❌ Не использовать `cd apps/frontend && yarn ...` chains в multi-command tool calls — `yarn --cwd <abs-path>` обязательно (F-013)
- ❌ Не удалять/изменять `Makefile` `lint-frontend-text` — CI gate для D-014
- ❌ Не использовать `time_to_overload_min` с одинаковой семантикой для всего stop — каждая карточка = свой трамвай (D-013)
