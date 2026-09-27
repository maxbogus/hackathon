---
id: T-232
phase: 4
title: Tables (historical + predictions) full width and height, column dividers, unclipped «Маршрут»
priority: P1
effort: 2
unit: hours
rice:
  R: 3
  I: 1.0
  C: 0.5
  score: 0.75
depends_on: []
blocks: []
tags: [frontend, ux, css-grid, tanstack-table, layout]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

# T-232: Tables full width/height + vertical column dividers + unclipped «Маршрут»

## Context

Заказчик открыл таблицы прогноза (`/predictions`) и исторических данных
(`/historical`) и вернул три замечания:

1. Таблица не занимает всю ширину — по бокам пустые поля (`maxWidth: 1400,
   margin: '0 auto'` в `PredictionsView.tsx` / `HistoricalView.tsx`).
2. Таблица не занимает всю высоту — фиксированные `height: 400px` в
   `scrollContainerStyle` обеих таблиц, ниже — пустое место.
3. Заголовок «Маршрут» всё ещё обрезается (колонка `110px` из T-231 + `overflow:
   hidden; textOverflow: ellipsis` в `thStyle`).
4. «Колонки должны быть по всей высоте» — нужны вертикальные разделители,
   идущие до низа таблицы (даже когда строк меньше, чем места).

## Acceptance Criteria

- [x] `/predictions` и `/historical`: таблица занимает всю ширину окна
      (`maxWidth: 1400`/`margin auto` убраны).
- [x] Таблица занимает всю высоту: высотная flex-цепочка
      `__root (minHeight:100vh, column)` → `main (flex:1, minHeight:0)` →
      страница (`flex:1, minHeight:0, column`) → таблица (`fillHeight`) →
      scroll-контейнер (`flex: 1 1 0`, `minHeight: 0`).
- [x] `fillHeight?: boolean` (default `false`) — standalone-рендер и тесты
      сохраняют прежние 400px.
- [x] `GRID_TEMPLATE_COLUMNS` route-колонка `110px` → `140px`; у `thStyle`
      убраны `overflow: hidden` + `textOverflow: ellipsis` → «Маршрут» не режется.
- [x] Вертикальные разделители колонок: `borderRight` у ячеек (кроме последней,
      `1fr`) + фон-линии scroll-контейнера на тех же x (140/260/320px), поэтому
      линии идут на всю высоту контейнера.
- [x] `fillHeight` и разделители покрыты тестами (по 4 новых теста в каждой
      таблице); шаблон колонок обновлён в ассертах.

## Technical Notes

- Фон-линии сделаны градиентами с зашитой позицией
  (`linear-gradient(to right, transparent 139px, #e5e7eb 139px 140px, transparent 140px)`),
  а не multi-layer `background-position`: его не поддерживает jsdom/cssstyle
  (в тестах вернул бы `''`), а браузер — да.
- `box-sizing` в проекте не сброшен (глобального CSS нет) — но block/flex-item
  с `width: auto`/`stretch` уже учитывает padding, так что переполнения нет.
- `<main>` во view-страницах заменён на `<section>`: уровень `main` даёт
  `__root.tsx`, вложенный `main` был невалидной семантикой.

## Verification

```bash
cd apps/frontend
yarn typecheck          # только 2 pre-existing ошибки routeCsv.ts
yarn test:run           # 283 passed / 2 pre-existing failed (routeCsv)
yarn lint               # только pre-existing (downloadCsv eqeqeq, HorizonToggle warn)
# от репо:
make frontend-text-check
make up   # /predictions, /historical: 100% ширина; таблица до низа экрана;
          # «Маршрут» целиком; вертикальные разделители на всю высоту
```

## Status

`in-progress` → `done` (перенесён в `docs/backlog/archive/`).
