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
 *   route  — 'Маршрут' (7 chars, bold) + стрелка сортировки « ▲» → 140px.
 *            T-232: было 110px — при крупном шрифте слово резалось в «Мар…».
 *            Фиксированные px обязательны: каждый virtualized-ряд — отдельный
 *            grid, поэтому max-content разъехал бы колонки между рядами.
 *   date   — 'YYYY-MM-DD' (10 chars) → 120px
 *   hour   — '0'..'23' → 60px
 *   value  — '1234.56' (7 chars) → 1fr (fills remainder)
 */
const GRID_TEMPLATE_COLUMNS = '140px 120px 60px 1fr';

/**
 * T-232: вертикальные разделители колонок. `COLUMN_BOUNDARIES_PX` — правые
 * границы route/date/hour (совпадают с `GRID_TEMPLATE_COLUMNS`), по ним
 * рисуются линии на всю высоту контейнера; те же x использует `borderRight`
 * у ячеек, поэтому линии совпадают и не удваиваются.
 */
const DIVIDER_COLOR = '#e5e7eb';
const CELL_DIVIDER = `1px solid ${DIVIDER_COLOR}`;
const COLUMN_BOUNDARIES_PX: readonly number[] = [140, 260, 320];

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

/**
 * T-232: контейнер скролла. При `fillHeight=true` растягивается на остаток
 * высоты страницы (`flex: 1 1 0` + `minHeight: 0`) — без магических
 * `calc(100vh - Npx)`, поэтому высота автоматически учитывает заголовок,
 * фильтры и footer. Иначе — прежние фиксированные 400px (standalone-рендер).
 *
 * Вертикальные разделители колонок рисуются фоном самого контейнера: фон
 * скролл-контейнера не уезжает при прокрутке контента (он привязан к
 * padding box), поэтому линии идут на всю высоту — даже если строк меньше,
 * чем места. Те же x-координаты использует `borderRight` у ячеек.
 */
function scrollContainerStyle(fillHeight: boolean): {
  readonly overflow: 'auto';
  readonly border: string;
  readonly borderRadius: number;
  readonly background: string;
  readonly position: 'relative';
  readonly backgroundImage: string;
  readonly backgroundSize: string;
  readonly backgroundRepeat: 'no-repeat';
  readonly flex?: string;
  readonly minHeight?: number;
  readonly height?: number;
} {
  return {
    ...(fillHeight ? { flex: '1 1 0', minHeight: 0 } : { height: VIRTUAL_CONTAINER_HEIGHT_PX }),
    overflow: 'auto' as const,
    border: '1px solid #e5e7eb',
    borderRadius: 4,
    background: '#fff',
    position: 'relative' as const,
    // Позиция линии зашита в сам градиент (`transparent → цвет → transparent`),
    // поэтому multi-layer background-position не нужен: его не поддерживает
    // jsdom/cssstyle (в тестах дал бы ''), а браузер — да.
    backgroundImage: COLUMN_BOUNDARIES_PX.map(
      (x) =>
        `linear-gradient(to right, transparent ${x - 1}px, ${DIVIDER_COLOR} ${x - 1}px ${x}px, transparent ${x}px)`,
    ).join(', '),
    backgroundSize: '100% 100%',
    backgroundRepeat: 'no-repeat' as const,
  };
}

/**
 * T-232: корень таблицы в режиме `fillHeight` — flex-колонка, чтобы
 * scroll-контейнер забрал всю высоту, оставшуюся от h2/фильтров/footer.
 */
const rootFillStyle = {
  display: 'flex',
  flexDirection: 'column',
  flex: '1 1 0',
  minHeight: 0,
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

/**
 * T-232: у заголовков убраны `overflow: hidden` + `textOverflow: ellipsis` —
 * «Маршрут» не должен резаться в «Мар…» ни при каком шрифте/зуме
 * (clinerule 32 R5: расширять колонку, а не сокращать слово).
 * `whiteSpace: nowrap` остаётся: заголовок не переносится, но и не обрезается.
 * У ячеек данных ellipsis сохраняется — там даты/числа фиксированной длины.
 */
const thStyle = {
  padding: '8px 12px',
  textAlign: 'left' as const,
  cursor: 'pointer',
  userSelect: 'none' as const,
  fontWeight: 600,
  whiteSpace: 'nowrap' as const,
} as const;

const tdStyle = {
  padding: '6px 12px',
  borderBottom: '1px solid #f1f5f9',
  whiteSpace: 'nowrap' as const,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
} as const;

/**
 * T-232: вертикальный разделитель колонки. У последней колонки (`value`, 1fr)
 * разделителя нет — правый край даёт border самого scroll-контейнера.
 */
function withColumnDivider<T extends Record<string, unknown>>(
  base: T,
  isLast: boolean,
): T & { borderRight: string } {
  return { ...base, borderRight: isLast ? 'none' : CELL_DIVIDER };
}

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
}
export interface PredictionsTableProps {
  readonly rows: readonly PredictionRow[];
  readonly isLoading?: boolean;
  readonly error?: string | null;
  readonly availableRoutes?: readonly number[];
  /**
   * T-232: `true` — таблица забирает всю высоту, оставшуюся от заголовков,
   * фильтров и footer (используется страницей /predictions). `false` (default)
   * — фиксированные 400px, как раньше (standalone-рендер, тесты).
   */
  readonly fillHeight?: boolean;
}

export function PredictionsTable({
  rows,
  isLoading = false,
  error = null,
  availableRoutes,
  fillHeight = false,
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
  return (
    <PredictionsTableInner rows={rows} availableRoutes={availableRoutes} fillHeight={fillHeight} />
  );
}

function PredictionsTableInner({
  rows,
  availableRoutes,
  fillHeight,
}: {
  readonly rows: readonly PredictionRow[];
  readonly availableRoutes?: readonly number[];
  readonly fillHeight: boolean;
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
    () => (showAllRoutes ? allRouteIds : allRouteIds.filter((r) => selectedRoutes.has(r))),
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
      style={fillHeight ? rootFillStyle : undefined}
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
        style={scrollContainerStyle(fillHeight)}
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
                {hg.headers.map((header, headerIndex) => {
                  const lastHeaderIndex = hg.headers.length - 1;
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
                      style={withColumnDivider(thStyle, headerIndex === lastHeaderIndex)}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
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
                  {row.getVisibleCells().map((cell, cellIndex, cells) => (
                    <div
                      role="cell"
                      key={cell.id}
                      style={withColumnDivider(tdStyle, cellIndex === cells.length - 1)}
                    >
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
