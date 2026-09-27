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
| T-225  | lib/roles.ts, lib/i18n/ru-RU.ts, routes/{__root,passenger,dispatcher}.tsx, App.test.tsx, routes/-__root.test.tsx, lib/i18n/t.test.ts | (rolePassenger.label→'Диспетчер', roleDispatcher block deleted, RoleId shrunk 3→2) | UX-rename: «Пассажир» в nav → «Диспетчер». Старая вкладка /dispatcher (AlertsPanel) убрана из nav как orphan-роут (прямой URL продолжает работать для дебага). Emoji в ROLES тоже перенесён →🎛️. Сам дашборд PassengerMode (passenger.modeTitle) сохраняет имя «Пассажир — нагрузка по линиям» — это название страницы, а не роль. |
| T-228  | api/downloadXlsx.ts, api/downloadCsv.ts (buildExportQuery), components/Charts/AnalystDashboard.tsx, lib/i18n/ru-RU.ts | analyst.{downloadXlsx,xlsxDownloaded,xlsxError} | XLSX-экспорт: вторая кнопка рядом с CSV, бинарный ответ через `customInstance({responseType:'blob'})`, скачивание Blob URL. Общий билдер query-строки для CSV/XLSX (DRY). |
| T-230  | components/Analyst/{GeneratePanel,HowItWorks}.tsx, components/Charts/{AnalystDashboard,PredictionsChart}.tsx, lib/predictionRuns.ts, lib/i18n/ru-RU.ts | analyst.{howItWorks*,activeSet*,generate*,candidate*,restoreEtalon*,recommendation*,chartFallbackNote,runStatusLabel} | Наборы прогнозов: генерация через Celery, кандидат → «Загрузить и сделать активным» / «Оставить эталон», активный набор + возврат эталона, описание «Как это работает» (`<details>`), фолбэк графика на активный набор с жёлтой подписью. |

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


| T-222  | components/Passenger/PredictionsTable.tsx, lib/predictionsTable.ts, components/Passenger/index.ts | passenger.predictionsTable.{title,searchPlaceholder,routesFilterLabel,columnRoute,columnDate,columnHour,columnValue,showAll,collapse,emptyMessage,loadErrorPrefix,rowsFooter,routesFooter,sortAsc,sortDesc,sortNone} | New TanStack Table v8 component + react-virtual for the full submission period (14640 rows). pure-UI component (rows prop), 5-min TanStack Query cache via lib/predictionsTable helper. Gentle default routes: {1,7,17,25}. Multi-select + globalFilter + sortable headers + loading/error/empty states. |

| T-222 follow-up | pages/PredictionsView.tsx, routes/predictions.tsx, lib/roles.ts | predictions.{viewTitle,viewHint}, app.rolePredictions.{label,description} | T-222 follow-up: PredictionsTable никуда не был подключён — добавили новую вкладку /predictions. pages/PredictionsView.tsx — обёртка useQuery(predictionsCsvQueryKey) + передача rows/isLoading/error в PredictionsTable. routes/predictions.tsx — file-based route. ROLES пополнен 3-й ролью "predictions" (). Только happy path — TanStack Query берёт helper из lib/predictionsTable.ts (5-min cache, frozen queryKey). |

| T-226  | components/Passenger/HistoricalTable.{tsx,test.tsx}, lib/historicalTable.{ts,test.ts}, pages/HistoricalView.tsx, routes/historical.tsx, routeTree.gen.ts, components/Passenger/index.ts, lib/roles.ts | app.roleHistorical.{label,description}, passenger.historicalTable.{title,routesFilterLabel,columnRoute,columnDate,columnHour,columnValue,showAll,collapse,emptyMessage,loadErrorPrefix,rowsFooter,routesFooter,sortAsc,sortDesc,sortNone}, historical.{viewTitle,viewHint} | Новая вкладка /historical — таблица фактических данных (actuals) за весь период наблюдений (68801 строка). Зеркало PredictionsTable без поиска (F-101), колонка «Факт» вместо «Прогноз». TanStack Table v8 + react-virtual, multi-select маршрутов (default {1,7,17,25}), sort, footer, loading/error/empty states. ROLES пополнен 4-й ролью "historical" (). data-testid префикс historical-table-*. Также удалён searchPlaceholder из passenger.predictionsTable (F-101: поиск глючил — multi-select маршрутов достаточно для 10 маршрутов). |
| T-122/T-227 | components/Map/{MapProvider,LeafletMap,YandexMap,types,mapColors,mapStrategy}.tsx, lib/geoRoutes.ts, pages/PassengerMode.tsx, components/Passenger/RouteLoadCard.tsx | map.{title,ariaLabel,hint,empty,noKey,routeLabel} | Карта маршрутов на дашборде «Диспетчер» (/passenger): Strategy OSM↔Yandex (D-003) через `VITE_MAP_IMPL`, геометрия из нового `GET /api/v1/geo/routes` (T-227), цвет/толщина = tier и load_pct из `/predictions/load` (та же палитра `loadTier.COLORS`, что у карточек). Клик по карточке ↔ подсветка маршрута на карте. `map.routeLabel` — функция (через `tf`). |
| T-231  | lib/labels.{ts,test.ts}, lib/i18n/ru-RU.ts, components/Filters/FiltersPanel.tsx, components/Analyst/GeneratePanel.tsx, components/Charts/PredictionsChart.tsx, components/Passenger/{RouteLoadCard,PredictionsTable,HistoricalTable}.tsx, pages/{PassengerMode,PredictionsView}.tsx | analyst.{featureLabels.*,featureHints.*,zeroLabels.*,zeroHints.*,modelLabels.*,featureSets.*,zerosOn,zerosOff,coefsTitle}; passenger.{side.*,actualsHeader,predictionsHeader,modeTitle,modeHint,\*,legend.\*}; historical.viewHint; common.unitPeople | Ревизия копирайта под требования Департамента транспорта (clinerule 32). В UI больше не протекают идентификаторы (`use_lag`, `with_all`, `zeros=ON`, `baseline_v1`, `test_submission_baseline`): новый `lib/labels.ts` маппит backend-имена в `TKey` с fallback на описание из API и generic де-снейкингом для неизвестных id. Англицизмы убраны («boardings» → «посадки», «WAPE-score» → «Точность (WAPE)», «Фичи» → «Факторы»), тон — официальный (убрано «и езжайте»), единицы измерения добавлены («Прогноз (чел.)», «чел.»), заголовок «Маршрут» больше не обрезается (grid 70px→110px в обеих таблицах). Raw `model_id` остаётся в `title=` (трассируемость). |
