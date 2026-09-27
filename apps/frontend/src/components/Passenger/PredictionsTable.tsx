/**
 * T-222: <PredictionsTable> — таблица прогнозов на весь submission-период.
 *
 * Архитектура (D-038):
 *  - Pure UI: данные через `rows` prop. Кэш — снаружи через TanStack Query.
 *  - Gentle default: routes {1, 7, 17, 25}, "Show all" button expands.
 *  - Виртуализация (@tanstack/react-virtual) — 14640 строк не лагают.
 *  - 4 колонки: route / date / hour / value, i18n через `t(...)`.
 *  - Сортировка кликом по header. globalFilter по всем колонкам.
 *  - Loading / error / empty states.
 */

import { useMemo, useRef, useState } from 'react';
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
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

const searchInputStyle = {
  flex: 1,
  minWidth: 200,
  padding: '6px 10px',
  border: '1px solid #cbd5e1',
  borderRadius: 4,
} as const;

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

const theadStyle = {
  position: 'sticky' as const,
  top: 0,
  background: '#f3f4f6',
  zIndex: 1,
} as const;

const thStyle = {
  padding: '8px 12px',
  textAlign: 'left' as const,
  borderBottom: '2px solid #e5e7eb',
  cursor: 'pointer',
  userSelect: 'none' as const,
} as const;

const tdStyle = {
  padding: '6px 12px',
  borderBottom: '1px solid #f1f5f9',
} as const;

/** Inline-style для virtualized row: absolute positioning с translateY. */
function virtualRowStyle(startPx: number): {
  readonly position: 'absolute';
  readonly top: 0;
  readonly transform: string;
  readonly width: string;
  readonly display: 'flex';
  readonly height: number;
} {
  return {
    position: 'absolute',
    top: 0,
    transform: `translateY(${startPx}px)`,
    width: '100%',
    display: 'flex',
    height: ROW_HEIGHT_PX,
  };
}

const ROW_HEIGHT_PX = 32;
const VIRTUAL_OVERSCAN = 10;

export interface PredictionsTableProps {
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
  const [globalFilter, setGlobalFilter] = useState('');
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
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: 'includesString',
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
        <input
          data-testid="predictions-table-search"
          type="search"
          placeholder={t('passenger.predictionsTable.searchPlaceholder')}
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          style={searchInputStyle}
        />
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
                  aria-label={`Маршрут ${rid}`}
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
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead style={theadStyle}>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const sortDir = header.column.getIsSorted();
                  const sortAttr =
                    sortDir === 'asc'
                      ? t('passenger.predictionsTable.sortAsc')
                      : sortDir === 'desc'
                        ? t('passenger.predictionsTable.sortDesc')
                        : t('passenger.predictionsTable.sortNone');
                  return (
                    <th
                      key={header.id}
                      role="columnheader"
                      data-sort={sortAttr}
                      onClick={header.column.getToggleSortingHandler()}
                      style={thStyle}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                      {sortDir === 'asc' ? ' ▲' : sortDir === 'desc' ? ' ▼' : ''}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody data-testid="predictions-table-body">
            <tr style={{ height: totalSize }} aria-hidden="true">
              <td colSpan={4} />
            </tr>
            {virtualRows.map((vr) => {
              const row = sortedRows[vr.index];
              if (!row) return null;
              return (
                <tr
                  key={row.id}
                  role="row"
                  data-index={vr.index}
                  style={virtualRowStyle(vr.start)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} style={tdStyle}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
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
