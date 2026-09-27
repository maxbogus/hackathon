---
id: T-222
phase: 4
title: Frontend PredictionsTable.tsx (TanStack Table) + LastDayCard.tsx
priority: P0
effort: 1
unit: hours
rice:
  R: 3
  I: 2
  C: 0.8
  score: 4.8
depends_on: [T-221]
blocks: [T-223]
tags: [frontend, tanstack-table, passenger, ui, clinerule-31]
status: ready
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-221 даёт типизированный массив `PredictionRow[]` из CSV. Теперь нужны **2 React-компонента**:

1. `<PredictionsTable rows={...} />` — таблица с TanStack Table v8 (уже в `package.json`:
   `@tanstack/react-table@8.20.0` + `@tanstack/react-virtual@3.10.0`). Колонки:
   route / date / hour / value. Фильтры + группировка по маршруту.
2. `<LastDayCard routeId date boardings variant="actual|prediction" />` — карточка
   «Маршрут N · дата · N чел» для секций «Как было» и «Как будет».

## Acceptance Criteria

- [ ] `apps/frontend/src/components/Passenger/PredictionsTable.tsx` создан
- [ ] `apps/frontend/src/components/Passenger/LastDayCard.tsx` создан
- [ ] Таблица рендерит `<table>` с 4 колонками: route / date / hour / value
- [ ] Сортировка по любой колонке (клик по header → `data-sort` атрибут)
- [ ] `globalFilter` — input с placeholder «Поиск...», фильтрует по всем колонкам
- [ ] `grouping=true` → сводная view, expandable rows по route_id
- [ ] `@tanstack/react-virtual` — таблица не лагает на 14640 строках
- [ ] LastDayCard показывает: «Маршрут N · YYYY-MM-DD · N чел»
- [ ] variant='actual' → data-variant='actual' (зелёный border), variant='prediction' → синий border
- [ ] vitest 4+ passed (`PredictionsTable.test.tsx` + `LastDayCard.test.tsx`)
- [ ] `yarn typecheck` 0 errors
- [ ] `yarn lint` без новых ошибок

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
