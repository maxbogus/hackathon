---
id: T-226
phase: 4
title: Frontend HistoricalTable.tsx + новая вкладка /historical
priority: P1
effort: 1
unit: hours
rice:
  R: 3
  I: 1
  C: 0.9
  score: 2.7
depends_on: [T-220, T-221, T-222]
blocks: []
tags: [frontend, tanstack-table, passenger, ui, clinerule-31]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-222 сделал PredictionsTable (TanStack Table v8 + react-virtual, 14640
строк прогнозов на отдельной вкладке /predictions). По аналогии нужна
такая же таблица для исторических данных (actuals): фактический
пассажиропоток за весь период наблюдений (68801 строк в actuals).

T-220 уже сделал backend endpoint /api/v1/historical/export.csv (тот же
формат route;date;hour;value), T-221 сделал fetchActualsCsv() в
routeCsv.ts. Frontend-часть осталась за бортом - actuals грузятся в
routeLoad.ts (агрегаты), но нет табличной формы.

Дополнительно: пользователь пожаловался, что поиск (text input +
globalFilter) в PredictionsTable работает глючно (F-101). В рамках этой
задачи убираем поиск из обеих таблиц (predictions + historical),
оставляем только multi-select маршрутов.

## Acceptance Criteria

- [ ] Поиск убран из PredictionsTable (нет input type=search, нет
      globalFilter state, нет searchPlaceholder i18n-ключа).
- [ ] HistoricalTable рендерит строки из fetchActualsCsv().
- [ ] Виртуализация работает (scroll container, virtualRows).
- [ ] Multi-select маршрутов работает (default = {1, 7, 17, 25}).
- [ ] Sort кликом по columnheader работает.
- [ ] Loading / error / empty states работают.
- [ ] Footer показывает "строк: N · маршрутов: M".
- [ ] На странице /historical есть ссылка в навигации (4-я вкладка).
- [ ] Тесты: HistoricalTable.test.tsx (RED-GREEN).
- [ ] Тесты: historicalTable.test.ts (RED-GREEN).
- [ ] Старые тесты PredictionsTable.test.tsx обновлены (убраны 2 globalFilter).
- [ ] yarn typecheck + yarn test:run + make frontend-text-check зелёные.
- [ ] Запись в docs/ledger/findings.jsonl (F-101: globalFilter удалён).
- [ ] Conventional Commit: feat(frontend): historical table + remove globalFilter (T-226).

## Technical Notes

- Структурно HistoricalTable ~95% дублирует PredictionsTable. Решение:
  явное дублирование (не выносить в общий DataTable ради DRY), т.к.
  они могут разойтись в будущем (исторические данные могут получить
  Delta к прогнозу колонку, predictions - другую).
- routeCsv.ts уже содержит fetchActualsCsv() - переиспользуем.
- data-testid префиксы: historical-table-* (отличаются от predictions-table-*).
- /api/v1/historical/export.csv возвращает ~68801 строк - виртуализация
  обязательна.

## Verification

cd /home/maxbogus/Repositories/hackathon/apps/frontend && yarn typecheck && yarn test:run
make frontend-text-check
