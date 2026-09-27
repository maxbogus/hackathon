/**
 * T-222: <PredictionsTable> — таблица прогнозов на весь submission-период.
 *
 * Архитектура (D-038 + D-039 / F-101):
 *  - Pure UI: данные через `rows` prop. Кэш — снаружи через TanStack Query.
 *  - Gentle default: routes {1, 7, 17, 25}, "Show all" button expands.
 *  - Виртуализация (@tanstack/react-virtual) — 14640 строк не лагают.
 *  - 4 колонки: route / date / hour / value, i18n через `t(...)`.
 *  - Сортировка кликом по header. НЕТ globalFilter (F-101: поиск глючил,
 *    multi-select маршрутов достаточно для 10 маршрутов).
 *  - Loading / error / empty states.
 */

import { useMemo, useRef, useState } from 'react';
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';

import { t, tf } from '@/lib/i18n/t';
import { Alert } from '@/lib/Alert';
import type { PredictionRow } from '@/lib/routeCsv';

/** D-038: щадящий выбор маршрутов (4 из 10, лучший WAPE-score). */
const DEFAULT_SELECTED_ROUTES: readonly number[] = [1, 7, 17, 25];
const VIRTUAL_CONTAINER_HEIGHT_PX = 400;

const ROW_HEIGHT_PX = 32;
const VIRTUAL_OVERSCAN = 10;

/**
 * D-038 / T-222 follow-up fix:
 * Unified column grid shared between header and data rows. Without this,
 * <th> (native table-layout) and <td> inside absolute-position virtual
 * rows (display:flex) used two different layout engines and columns
 * misaligned. CSS Grid shares one template across header and all rows,
 * including virtualized.
 *
 * Empirical column widths (chosen by content):
 *   route  — 'Маршрут' (7 chars, bold) needs ~110px, otherwise CSS ellipsis
 *            turns the header into «Мар…» (T-231)
 *   date   — 'YYYY-MM-DD' (10 chars) → 120px
 *   hour   — '0'..'23' → 60px
 *   value  — '1234.56' (7 chars) → 1fr (fills remainder)
 */
const GRID_TEMPLATE_COLUMNS = '110px 120px 60px 1fr';

const fieldsetStyle = {
  border: '1px solid #cbd5e1',
  borderRadius: 4,
  padding: '4px 8px',
  display: 'flex' as const,
  flexWrap: 'wrap' as const,
  gap: 6,
  alignItems: 'center',
} as const;

const checkboxLabelStyle = {
  display: 'inline-flex' as const,
  alignItems: 'center',
  gap: 4,
  fontSize: 13,
  cursor: 'pointer',
} as const;

const buttonStyle = {
  padding: '4px 10px',
  background: '#4f46e5',
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 13,
} as const;

const scrollContainerStyle = {
  height: VIRTUAL_CONTAINER_HEIGHT_PX,
  overflow: 'auto',
  border: '1px solid #e5e7eb',
  borderRadius: 4,
  background: '#fff',
  position: 'relative' as const,
} as const;

/**
 * T-222 follow-up: <div role="table"> wrapper. CSS Grid shares one
 * `grid-template-columns = GRID_TEMPLATE_COLUMNS` between header and all
 * data rows (including virtualized). Solves the column-misalignment bug
 * that was visible at <thead><th> vs <tbody><tr><td> with display:flex.
 */
const tableStyle = {
  display: 'grid',
  width: '100%',
  fontSize: 14,
} as const;

/**
 * Sticky header внутри scroll container. position:sticky + top:0
 * через вложенный row делает header видимым при скролле rows.
 */
const headerGroupStyle = {
  position: 'sticky' as const,
  top: 0,
  zIndex: 2,
  background: '#f3f4f6',
  display: 'grid',
};

const headerRowStyle = {
  display: 'grid',
  gridTemplateColumns: GRID_TEMPLATE_COLUMNS,
  borderBottom: '2px solid #e5e7eb',
} as const;

const thStyle = {
  padding: '8px 12px',
  textAlign: 'left' as const,
  cursor: 'pointer',
  userSelect: 'none' as const,
  fontWeight: 600,
  whiteSpace: 'nowrap' as const,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
} as const;

const tdStyle = {
  padding: '6px 12px',
  borderBottom: '1px solid #f1f5f9',
  whiteSpace: 'nowrap' as const,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
} as const;

/**
 * Inline-style для virtualized row: absolute positioning с translateY,
 * внутри — display:grid с тем же GRID_TEMPLATE_COLUMNS, что и header.
 * Это и есть фикс — общий шаблон выравнивает колонки.
 */
function virtualRowStyle(startPx: number): {
  readonly position: 'absolute';
  readonly top: 0;
  readonly transform: string;
  readonly left: 0;
  readonly right: 0;
  readonly display: 'grid';
  readonly gridTemplateColumns: string;
  readonly height: number;
} {
  return {
    position: 'absolute',
    top: 0,
    transform: `translateY(${startPx}px)`,
    left: 0,
    right: 0,
    display: 'grid',
    gridTemplateColumns: GRID_TEMPLATE_COLUMNS,
    height: ROW_HEIGHT_PX,
  };
}export interface PredictionsTableProps {
  readonly rows: readonly PredictionRow[];
  readonly isLoading?: boolean;
  readonly error?: string | null;
  readonly availableRoutes?: readonly number[];
}

export function PredictionsTable({
  rows,
  isLoading = false,
  error = null,
  availableRoutes,
}: PredictionsTableProps): JSX.Element {
  if (isLoading) {
    return (
      <p data-testid="predictions-table-loading" role="status">
        {t('common.loading')}
      </p>
    );
  }
  if (error) {
    return (
      <Alert severity="warning" testId="predictions-table-error">
        {t('passenger.predictionsTable.loadErrorPrefix')} {error}
      </Alert>
    );
  }
  if (rows.length === 0) {
    return (
      <p data-testid="predictions-table-empty" role="status">
        {t('passenger.predictionsTable.emptyMessage')}
      </p>
    );
  }
  return <PredictionsTableInner rows={rows} availableRoutes={availableRoutes} />;
function PredictionsTableInner({
  rows,
  availableRoutes,
}: {
  readonly rows: readonly PredictionRow[];
  readonly availableRoutes?: readonly number[];
}): JSX.Element {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [showAllRoutes, setShowAllRoutes] = useState(false);
  const [selectedRoutes, setSelectedRoutes] = useState<Set<number>>(
    () => new Set(DEFAULT_SELECTED_ROUTES),
  );

  const allRouteIds = useMemo<readonly number[]>(() => {
    if (availableRoutes && availableRoutes.length > 0) return availableRoutes;
    const set = new Set<number>();
    for (const r of rows) set.add(r.routeId);
    return Array.from(set).sort((a, b) => a - b);
  }, [rows, availableRoutes]);

  const visibleRoutes = useMemo<readonly number[]>(
    () =>
      showAllRoutes
        ? allRouteIds
        : allRouteIds.filter((r) => selectedRoutes.has(r)),
    [allRouteIds, showAllRoutes, selectedRoutes],
  );

  const filteredRows = useMemo<PredictionRow[]>(() => {
    const allowed = new Set(visibleRoutes);
    return rows.filter((r) => allowed.has(r.routeId));
  }, [rows, visibleRoutes]);

  const columns = useMemo<ColumnDef<PredictionRow>[]>(
    () => [
      {
        accessorKey: 'routeId',
        header: () => t('passenger.predictionsTable.columnRoute'),
        cell: (info) => info.getValue<number>(),
      },
      {
        accessorKey: 'date',
        header: () => t('passenger.predictionsTable.columnDate'),
        cell: (info) => info.getValue<string>(),
      },
      {
        accessorKey: 'hour',
        header: () => t('passenger.predictionsTable.columnHour'),
        cell: (info) => info.getValue<number>(),
      },
      {
        accessorKey: 'value',
        header: () => t('passenger.predictionsTable.columnValue'),
        cell: (info) => info.getValue<number>().toFixed(2),
      },
    ],
    [],
  );

  const table = useReactTable<PredictionRow>({
    data: filteredRows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  const sortedRows = table.getRowModel().rows;

  const parentRef = useRef<HTMLDivElement | null>(null);
  const virtualizer = useVirtualizer({
    count: sortedRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT_PX,
    overscan: VIRTUAL_OVERSCAN,
  });
  const virtualRows = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();

  const toggleRoute = (rid: number): void => {
    setSelectedRoutes((prev) => {
      const next = new Set(prev);
      if (next.has(rid)) next.delete(rid);
      else next.add(rid);
      return next;
    });
  };

return (
    <div
      data-testid="predictions-table"
      role="region"
      aria-label={t('passenger.predictionsTable.title')}
    >
      <h2 style={{ marginTop: 0 }}>{t('passenger.predictionsTable.title')}</h2>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
        <fieldset style={fieldsetStyle}>
          <legend style={{ padding: '0 6px', fontSize: 13 }}>
            {t('passenger.predictionsTable.routesFilterLabel')}
          </legend>
          {allRouteIds.map((rid) => {
            const isChecked = showAllRoutes || selectedRoutes.has(rid);
            return (
              <label
                key={rid}
                data-testid={`predictions-table-route-${rid}`}
                style={checkboxLabelStyle}
              >
                <input
                  type="checkbox"
                  aria-label={tf('map.routeLabel', rid)}
                  checked={isChecked}
                  disabled={showAllRoutes}
                  onChange={() => toggleRoute(rid)}
                />
                <span>{rid}</span>
              </label>
            );
          })}
          {showAllRoutes ? (
            <button
              type="button"
              onClick={() => setShowAllRoutes(false)}
              data-testid="predictions-table-collapse"
              style={buttonStyle}
            >
              {t('passenger.predictionsTable.collapse')}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setShowAllRoutes(true)}
              data-testid="predictions-table-show-all"
              style={buttonStyle}
            >
              {t('passenger.predictionsTable.showAll')}
            </button>
          )}
        </fieldset>
      </div>

<div
        ref={parentRef}
        data-testid="predictions-table-scroll"
        style={scrollContainerStyle}
      >
        {/*
          T-222 follow-up: <table>/<thead>/<tbody> заменены на семантический
          ARIA-эквивалент с CSS Grid. Нативный <table> + display:flex в absolute
          строках давали рассинхрон колонок; Grid делит один шаблон между
          header и всеми rows, включая virtualized.
          ARIA roles сохраняются для screen readers (W3C pattern).
        */}
        <div role="table" aria-rowcount={sortedRows.length} style={tableStyle}>
          {/* ── Header (sticky внутри scroll container) ───────────── */}
          <div role="rowgroup" style={headerGroupStyle}>
            {table.getHeaderGroups().map((hg) => (
              <div
                key={hg.id}
                role="row"
                data-testid="predictions-table-header"
                data-grid-template-columns={GRID_TEMPLATE_COLUMNS}
                style={headerRowStyle}
              >
                {hg.headers.map((header) => {
                  const sortDir = header.column.getIsSorted();
                  const sortAttr =
                    sortDir === 'asc'
                      ? t('passenger.predictionsTable.sortAsc')
                      : sortDir === 'desc'
                        ? t('passenger.predictionsTable.sortDesc')
                        : t('passenger.predictionsTable.sortNone');
                  return (
                    <div
                      key={header.id}
                      role="columnheader"
                      data-sort={sortAttr}
                      onClick={header.column.getToggleSortingHandler()}
                      style={thStyle}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                      {sortDir === 'asc' ? ' ▲' : sortDir === 'desc' ? ' ▼' : ''}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {/* ── Body (virtualized) ──────────────────────────────── */}
          <div
            role="rowgroup"
            data-testid="predictions-table-body"
            style={{ position: 'relative', height: totalSize }}
          >
            {virtualRows.map((vr) => {
              const row = sortedRows[vr.index];
              if (!row) return null;
              return (
                <div
                  key={row.id}
                  role="row"
                  data-testid="predictions-table-row"
                  data-index={vr.index}
                  data-grid-template-columns={GRID_TEMPLATE_COLUMNS}
                  style={virtualRowStyle(vr.start)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <div role="cell" key={cell.id} style={tdStyle}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p
        data-testid="predictions-table-footer"
        style={{ marginTop: 8, fontSize: 13, color: '#64748b' }}
      >
        {tf('passenger.predictionsTable.rowsFooter', filteredRows.length)}
        {' · '}
        {tf('passenger.predictionsTable.routesFooter', visibleRoutes.length)}
      </p>
    </div>
  );
}


}
