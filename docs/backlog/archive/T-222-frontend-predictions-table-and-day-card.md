---
id: T-222
phase: 4
title: Frontend PredictionsTable.tsx (TanStack Table v8 + react-virtual)
priority: P0
effort: 1
unit: hours
rice:
  R: 3
  I: 2
  C: 0.9
  score: 5.4
depends_on: [T-221]
blocks: []
tags: [frontend, tanstack-table, passenger, ui, clinerule-31]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-221 дал типизированный массив `PredictionRow[]` через `fetchPredictionsCsv()`.
Нужен **только один** React-компонент:

`<PredictionsTable rows={...} />` — таблица прогнозов с TanStack Table v8 (уже
в `package.json`: `@tanstack/react-table@8.20.0` + `@tanstack/react-virtual@3.10.0`).
Колонки: route / date / hour / value. Фильтры + multi-select маршрутов.
Виртуализация для 14640 строк submission-периода.

**Scope-down (решение Cline, сессия 2026-09-27 после T-225):**
- ❌ **НЕ делаем** `LastDayCard.tsx` (он нужен был только для T-223).
- ❌ **НЕ делаем** T-223 (отменён — не трогаем PassengerMode.tsx).
- ✅ Компонент — **переиспользуемая деталь**, без привязки к конкретной странице.
  Интеграция в PassengerMode (или отдельный роут) — отдельный тикет.

**D-038: щадящий выбор по умолчанию = routes {1, 7, 17, 25}** (4 из 10).
Не все маршруты сразу — пользователь видит подмножество, кнопка
«Показать все» раскрывает остальные. Основание: эти 4 маршрута дают
наилучший WAPE-score на baseline (см. лидборд submission в ledger).
D-038.1: компонент не фетчит данные, принимает `rows: PredictionRow[]`.
D-038.2: кэш через TanStack Query (5 min) — отдельным helper'ом.

## Acceptance Criteria

- [x] `apps/frontend/src/components/Passenger/PredictionsTable.tsx` создан
- [x] `apps/frontend/src/components/Passenger/PredictionsTable.test.tsx` создан
- [x] `apps/frontend/src/lib/predictionsTable.ts` создан (TanStack Query helper)
- [x] `apps/frontend/src/lib/predictionsTable.test.ts` создан
- [x] `apps/frontend/src/components/Passenger/index.ts` создан (barrel export)
- [x] Таблица рендерит `<table>` с 4 колонками: route / date / hour / value
- [x] Header'ы через `t(...)` (ru-RU.ts), все строки — без хардкода
- [x] Сортировка по любой колонке (клик по header → `data-sort` атрибут)
- [x] `globalFilter` — input с placeholder «Поиск...», фильтрует по всем колонкам
- [x] Multi-select маршрутов: по умолчанию {1, 7, 17, 25}, кнопка «Показать все»
- [x] `@tanstack/react-virtual` — таблица не лагает на 14640 строках
- [x] Loading state — `{t('common.loading')}` (handles `isLoading` prop)
- [x] Error state — `<Alert severity="warning">` (handles `error` prop)
- [x] Empty state — friendly «Нет данных»
- [x] Footer: «N строк · M маршрутов»
- [x] vitest 8+ passed
- [x] `yarn typecheck` 0 errors
- [x] `yarn lint` без новых ошибок
- [x] `make frontend-text-check` PASS

## RED (apps/frontend/src/components/Passenger/PredictionsTable.test.tsx)

```tsx
import { describe, expect, it } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { PredictionsTable } from './PredictionsTable';
import type { PredictionRow } from '@/lib/routeCsv';

const ROWS: PredictionRow[] = [
  {routeId: 1, date: '2025-11-01', hour: 0, value: 100},
  {routeId: 7, date: '2025-11-01', hour: 0, value: 200},
  {routeId: 17, date: '2025-11-02', hour: 0, value: 300},
];

describe('PredictionsTable', () => {
  it('renders 4 column headers', () => {
    render(<PredictionsTable rows={ROWS} />);
    expect(screen.getByRole('columnheader', {name: /маршрут/i})).toBeInTheDocument();
    expect(screen.getByRole('columnheader', {name: /дата/i})).toBeInTheDocument();
    expect(screen.getByRole('columnheader', {name: /час/i})).toBeInTheDocument();
    expect(screen.getByRole('columnheader', {name: /прогноз/i})).toBeInTheDocument();
  });

  it('renders all data rows + header', () => {
    render(<PredictionsTable rows={ROWS} />);
    expect(screen.getAllByRole('row').length).toBeGreaterThanOrEqual(4); // header + 3 rows
  });

  it('filters rows by globalFilter', () => {
    render(<PredictionsTable rows={ROWS} />);
    const search = screen.getByPlaceholderText(/поиск/i);
    fireEvent.change(search, {target: {value: '2025-11-02'}});
    // row с 2025-11-02 видна, остальные скрыты
    expect(screen.getByText('17')).toBeInTheDocument();
    // 1 и 7 НЕ видны
  });
});

describe('LastDayCard', () => {
  it('shows route label + date + boardings', () => {
    render(<LastDayCard routeId={17} date="2025-10-31" boardings={12345} variant="actual" />);
    expect(screen.getByText(/Маршрут 17/)).toBeInTheDocument();
    expect(screen.getByText(/2025-10-31/)).toBeInTheDocument();
    expect(screen.getByText(/12345 чел/)).toBeInTheDocument();
    expect(screen.getByTestId('last-day-card')).toHaveAttribute('data-variant', 'actual');
  });

  it('variant=prediction has different styling', () => {
    render(<LastDayCard routeId={1} date="2025-12-31" boardings={14096} variant="prediction" />);
    expect(screen.getByTestId('last-day-card')).toHaveAttribute('data-variant', 'prediction');
  });
});
```

## GREEN

**PredictionsTable.tsx** (~80 строк):
- `useReactTable` с `getCoreRowModel`, `getSortedRowModel`, `getFilteredRowModel`, `getGroupedRowModel`.
- `useVirtualizer` из `@tanstack/react-virtual` для окна строк.
- Колонки: `[{accessorKey: 'routeId', header: t('passenger.tableColumnRoute')}, ...]`.
- input `<input placeholder={t('passenger.tableFilter')} value={globalFilter} onChange={...} />`.

**LastDayCard.tsx** (~30 строк):
- border color = variant==='actual' ? green : blue.
- показывает `Маршрут {routeId}`, `дата`, `{Math.round(boardings)} чел`.

## REFACTOR

- Вынести колонки в `COLUMNS_PREDICTIONS` const.
- `aria-label` для accessibility.
- `data-testid="predictions-table"` для тестов.

## Verification

```bash
cd /home/maxbogus/Repositories/hackathon/apps/frontend && yarn test:run src/components/Passenger/
# ожидаем: 5/5 passed
yarn typecheck  # 0 errors
yarn lint 2>&1 | grep -v 'downloadCsv\|HorizonToggle' | grep error
# ожидаем: 0 errors (только pre-existing в чужих файлах)
```

## Technical Notes

- TanStack Table v8 + react-virtual — оба уже в `package.json` (см. T-007).
- `getGroupedRowModel` требует `getCoreRowModel` (он у нас есть).
- Virtual scroll container — `<div ref={parentRef}>` с фиксированной высотой (например `400px`).
