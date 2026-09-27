# i18n Migration Log — apps/frontend/src/lib/i18n

Records every UI-string migration away from JSX literals into the `TEXTS`
dictionary (T-141). Read this when:

- Adding a new component with user-visible text.
- Wondering whether `t("...")` or `tf("...", n)` is the right call.
- Verifying the CI gate (`make frontend-text-check`) won't false-positive.

| Ticket | File(s)                                                                                              | Keys added                                                   | Notes                                                                                                                   |
| ------ | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| T-141  | App.tsx, components/Dispatcher/{AlertsPanel,AlertCard}.tsx, pages/PassengerMode.tsx, lib/EtaCard.tsx | app._, dispatcher.alerts._, passenger.*, common.minutesShort | Initial migration — 30+ keys, hybrid `t()` lookup introduced. `recommend.ts` left as pure logic (data, not UI literal). |
| T-196  | components/Charts/{HistoricalChart,PredictionsChart,AnalystDashboard}.tsx, components/Filters/FiltersPanel.tsx, routes/analyst.tsx | analyst.*, common.{loading,errorPrefix,retry,yes,no} | Analyst dashboard — historical + predictions charts, feature toggles + zero overrides + coef_* sliders, Download CSV button. Replaces PlaceholderPanel for /analyst. |
| T-200  | lib/roles.ts, lib/i18n/ru-RU.ts, App.test.tsx, routes/-__root.test.tsx, routes/{analyst,dispatcher}.tsx | (rolePlanner block deleted, RoleId shrunk 4→3) | Dropped planner tab from navigation. PlaceholderPanel component and routes/planner.tsx removed. Three working dashboards remain: passenger, dispatcher, analyst. |
| T-201  | lib/activeModel.{ts,test.ts}, pages/PassengerMode.{tsx,test.ts}, lib/i18n/ru-RU.ts | passenger.activeModelFooter, lib/activeModel.ts | Active model fetched from /api/v1/models/active on mount; footer shows model id + WAPE-score (was hard-coded "—"). Silent failure → fallback to ETA's model_id. |
| T-203  | components/Filters/HorizonGranularity.{tsx,test.ts}, components/Charts/{PredictionsChart,AnalystDashboard}.tsx, lib/i18n/ru-RU.ts | analyst.horizon{Label,Day,Month,Year}, analyst.granularity{Label,Hour,Day,Month} | New controlled selector for horizon (day/month/year) + granularity (hour/day/month). Wired to /api/v1/predictions/db/{route_id} query params. |
| T-225  | lib/roles.ts, lib/i18n/ru-RU.ts, routes/{__root,passenger,dispatcher}.tsx, App.test.tsx, routes/-__root.test.tsx, lib/i18n/t.test.ts | (rolePassenger.label→'Диспетчер', roleDispatcher block deleted, RoleId shrunk 3→2) | UX-rename: «Пассажир» в nav → «Диспетчер». Старая вкладка /dispatcher (AlertsPanel) убрана из nav как orphan-роут (прямой URL продолжает работать для дебага). Emoji в ROLES тоже перенесён 🧍→🎛️. Сам дашборд PassengerMode (passenger.modeTitle) сохраняет имя «Пассажир — нагрузка по линиям» — это название страницы, а не роль. |

## Conventions

- **Static copy** → `t("namespace.leaf")`.
- **Interpolation / templates** → `tf("namespace.leaf", arg1, arg2)`.
- **Pure-logic strings** (e.g. `recommend.ts`) stay in source — clinerule 20
  carves out `lib/` (pure logic) from the registry. Test fixtures reference
  these via `expect(...).toMatch(...)` against literals.
- **Type safety** — the `TKey` union is generated from `TEXTS`. Renaming a
  key produces compile errors at every call site, so renames are atomic.

## What is **not** a violation

- JSON in `src/mocks/*.json` (mock data, not UI code).
- Comments inside `.tsx` / `.ts` (JSDoc, leading `*`).
- Test fixtures asserting against Russian copy (e.g.
  `expect(text).toContain("садитесь")`).

The CI gate (`make frontend-text-check`) excludes all of these.
