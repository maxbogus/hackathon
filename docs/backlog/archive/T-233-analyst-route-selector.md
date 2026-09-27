---
id: T-233
phase: 4
title: Route selector on analyst dashboard
priority: P1
effort: 2
unit: hours
rice:
  R: 3
  I: 1
  C: 0.9
  score: 1.35
depends_on: [T-196, T-218]
blocks: []
tags: [frontend, analyst, ux]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

Экран «Аналитик» (`/analyst`, T-196) был жёстко привязан к маршруту 7:
`AnalystDashboard.tsx` держал `const [routeId] = useState(DEFAULT_ROUTE)` —
сеттер объявлен, но не использовался, а `FiltersPanel` печатал статичную
строку «Маршрут: **7**».

При этом оба графика уже принимают `routeId` пропом и включают его в
`queryKey`/URL, то есть после подключения селектора они рефетчатся
автоматически — не хватало только UI-переключателя и списка маршрутов.

Список маршрутов = **объединение** маршрутов, по которым есть данные:
`GET /api/v1/historical` (фактические посадки) ∪ `GET /api/v1/predictions/load`
(прогнозы). Если оба источника недоступны/пусты — канонические 10 маршрутов
хакатона (F-045, clinerule 23 R6), чтобы селект никогда не был пустым.

## Acceptance Criteria

- [x] На `/analyst` вместо «Маршрут: **7**» — `<select data-testid="route-select">`
      со списком маршрутов; значение по умолчанию — 7.
- [x] Смена маршрута обновляет оба графика (историю и прогноз) без перезагрузки
      страницы.
- [x] Список = объединение `/historical` и `/predictions/load`, отсортирован,
      без дублей.
- [x] Если один источник упал — список формируется из второго.
- [x] Если оба упали/пусты — список = `CANONICAL_ROUTES` (10 маршрутов).
- [x] Текущий выбранный маршрут всегда есть в списке опций.
- [x] При сбое `/api/v1/features` селектор маршрута и коэффициенты остаются
      рабочими (ранний `return` в `FiltersPanel` больше не скрывает весь aside).
- [x] `make frontend-text-check` зелёный (нет русских строк вне `lib/i18n/`).

## Technical Notes

- `lib/routeCatalog.ts` — новый data-layer, зеркало `lib/routeLoad.ts` /
  `lib/geoRoutes.ts`: никогда не бросает, graceful fallback.
- `components/Filters/RouteSelect.tsx` — pure controlled компонент, зеркало
  `HorizonGranularity.tsx` (родитель владеет состоянием).
- `AnalystDashboard` остаётся единственным местом «fetch + React» — состояние
  маршрута живёт здесь (как коэффициенты и horizon/granularity).
- Никаких изменений в backend / OpenAPI / `generated/`: контракты уже есть.

## Verification

```bash
cd apps/frontend && yarn test:run && yarn typecheck && yarn lint
make frontend-text-check
# в браузере: make up → http://localhost:5173/analyst → выбрать маршрут 1/17/50
```

## Status

`done` — 2026-09-27. Проверки: `yarn test:run` (16 новых тестов, всего 298 passed;
2 падения в `lib/routeCsv.test.ts` — предсуществующие, скоуп T-221),
`yarn prettier --check` / `yarn eslint` на новых и изменённых файлах — чисто,
`make frontend-text-check` — зелёный.
