/**
 * T-226: <HistoricalTable> — таблица исторических данных (actuals) за весь период.
 *
 * Архитектура (D-038 + D-039):
 *  - Pure UI: данные через `rows` prop. Кэш — снаружи через TanStack Query.
 *  - Gentle default: routes {1, 7, 17, 25}, "Show all" button expands.
 *  - Виртуализация (@tanstack/react-virtual) — 68801 строк не лагают.
 *  - 4 колонки: route / date / hour / Факт (НЕ «Прогноз»), i18n через `t(...)`.
 *  - Сортировка кликом по header. НЕТ globalFilter (F-101: поиск убран).
 *  - Loading / error / empty states.
 *  - data-testid префикс `historical-table-*` (отличается от PredictionsTable).
 *
 * Явное дублирование с PredictionsTable (не выносим общий DataTable) —
 * таблицы могут разойтись (исторические данные могут получить «Δ к
 * прогнозу» колонку, predictions — другую).
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
 * T-226: тот же шаблон колонок, что и PredictionsTable (route/date/hour/value).
 * CSS Grid делит один шаблон между header и всеми data rows, включая virtualized.
 *
 * T-232: route-колонка расширена 110px → 140px — «Маршрут» + стрелка сортировки
 * « ▲» перестают урезаться в «Мар…» (clinerule 32 R5). Ширины фиксированные:
 * каждый virtualized-ряд — отдельный grid, `max-content` разъехал бы колонки.
 */
const GRID_TEMPLATE_COLUMNS = '140px 120px 60px 1fr';

/**
 * T-232: вертикальные разделители колонок. `COLUMN_BOUNDARIES_PX` — правые
 * границы route/date/hour (совпадают с `GRID_TEMPLATE_COLUMNS`): по ним
 * рисуются линии на всю высоту контейнера, те же x использует `borderRight`
 * у ячеек, поэтому линии не удваиваются.
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
 * `calc(100vh - Npx)`: высота автоматически учитывает заголовок, фильтры и
 * footer. Иначе — прежние фиксированные 400px (standalone-рендер, тесты).
 *
 * Вертикальные разделители колонок рисуются фоном самого контейнера: фон
 * скролл-контейнера не уезжает при прокрутке контента (привязан к padding
 * box), поэтому линии идут на всю высоту — даже если строк меньше, чем места.
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
 * T-222 follow-up (применён здесь): <div role="table"> wrapper. CSS Grid
 * делит один `grid-template-columns = GRID_TEMPLATE_COLUMNS` между header
 * и всеми data rows (включая virtualized). Решает баг рассинхрона колонок.
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

export interface HistoricalTableProps {
  readonly rows: readonly PredictionRow[];
  readonly isLoading?: boolean;
  readonly error?: string | null;
  readonly availableRoutes?: readonly number[];
  /**
   * T-232: `true` — таблица забирает всю высоту, оставшуюся от заголовков,
   * фильтров и footer (используется страницей /historical). `false` (default)
   * — фиксированные 400px, как раньше (standalone-рендер, тесты).
   */
  readonly fillHeight?: boolean;
}

export function HistoricalTable({
  rows,
  isLoading = false,
  error = null,
  availableRoutes,
  fillHeight = false,
}: HistoricalTableProps): JSX.Element {
  if (isLoading) {
    return (
      <p data-testid="historical-table-loading" role="status">
        {t('common.loading')}
      </p>
    );
  }
  if (error) {
    return (
      <Alert severity="warning" testId="historical-table-error">
        {t('passenger.historicalTable.loadErrorPrefix')} {error}
      </Alert>
    );
  }
  if (rows.length === 0) {
    return (
      <p data-testid="historical-table-empty" role="status">
        {t('passenger.historicalTable.emptyMessage')}
      </p>
    );
  }
  return (
    <HistoricalTableInner rows={rows} availableRoutes={availableRoutes} fillHeight={fillHeight} />
  );
}

function HistoricalTableInner({
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
    return Array.from(new Set(rows.map((r) => r.routeId))).sort((a, b) => a - b);
  }, [rows, availableRoutes]);

  const routeFilteredRows = useMemo<readonly PredictionRow[]>(() => {
    if (showAllRoutes) return rows;
    return rows.filter((r) => selectedRoutes.has(r.routeId));
  }, [rows, selectedRoutes, showAllRoutes]);

  const visibleRoutes = useMemo<readonly number[]>(() => {
    if (showAllRoutes) return allRouteIds;
    return allRouteIds.filter((rid) => selectedRoutes.has(rid));
  }, [allRouteIds, selectedRoutes, showAllRoutes]);

  const columns = useMemo<ColumnDef<PredictionRow>[]>(
    () => [
      {
        accessorKey: 'routeId',
        header: t('passenger.historicalTable.columnRoute'),
        cell: (info) => info.getValue<number>(),
      },
      {
        accessorKey: 'date',
        header: t('passenger.historicalTable.columnDate'),
        cell: (info) => info.getValue<string>(),
      },
      {
        accessorKey: 'hour',
        header: t('passenger.historicalTable.columnHour'),
        cell: (info) => info.getValue<number>(),
      },
      {
        accessorKey: 'value',
        header: t('passenger.historicalTable.columnValue'),
        cell: (info) => info.getValue<number>().toFixed(2),
      },
    ],
    [],
  );

  const table = useReactTable<PredictionRow>({
    data: routeFilteredRows as PredictionRow[],
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
      data-testid="historical-table"
      role="region"
      aria-label={t('passenger.historicalTable.title')}
      style={fillHeight ? rootFillStyle : undefined}
    >
      <h2 style={{ marginTop: 0 }}>{t('passenger.historicalTable.title')}</h2>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
        <fieldset style={fieldsetStyle}>
          <legend style={{ padding: '0 6px', fontSize: 13 }}>
            {t('passenger.historicalTable.routesFilterLabel')}
          </legend>
          {allRouteIds.map((rid) => {
            const isChecked = showAllRoutes || selectedRoutes.has(rid);
            return (
              <label
                key={rid}
                data-testid={`historical-table-route-${rid}`}
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
              data-testid="historical-table-collapse"
              style={buttonStyle}
            >
              {t('passenger.historicalTable.collapse')}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setShowAllRoutes(true)}
              data-testid="historical-table-show-all"
              style={buttonStyle}
            >
              {t('passenger.historicalTable.showAll')}
            </button>
          )}
        </fieldset>
      </div>

      <div
        ref={parentRef}
        data-testid="historical-table-scroll"
        style={scrollContainerStyle(fillHeight)}
      >
        {/*
          CSS Grid <div role="table"> wrapper. Header и data rows используют
          общий grid-template-columns → колонки выровнены (включая
          virtualized rows с absolute positioning).
          ARIA roles сохраняются для screen readers (W3C pattern).
        */}
        <div role="table" aria-rowcount={sortedRows.length} style={tableStyle}>
          {/* ── Header (sticky внутри scroll container) ───────────── */}
          <div role="rowgroup" style={headerGroupStyle}>
            {table.getHeaderGroups().map((hg) => (
              <div
                key={hg.id}
                role="row"
                data-testid="historical-table-header"
                data-grid-template-columns={GRID_TEMPLATE_COLUMNS}
                style={headerRowStyle}
              >
                {hg.headers.map((header, headerIndex) => {
                  const lastHeaderIndex = hg.headers.length - 1;
                  const sortDir = header.column.getIsSorted();
                  const sortAttr =
                    sortDir === 'asc'
                      ? t('passenger.historicalTable.sortAsc')
                      : sortDir === 'desc'
                        ? t('passenger.historicalTable.sortDesc')
                        : t('passenger.historicalTable.sortNone');
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
            data-testid="historical-table-body"
            style={{ position: 'relative', height: totalSize }}
          >
            {virtualRows.map((vr) => {
              const row = sortedRows[vr.index];
              if (!row) return null;
              return (
                <div
                  key={row.id}
                  role="row"
                  data-testid="historical-table-row"
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
        data-testid="historical-table-footer"
        style={{ marginTop: 8, fontSize: 13, color: '#64748b' }}
      >
        {tf('passenger.historicalTable.rowsFooter', sortedRows.length)}
        {' · '}
        {tf('passenger.historicalTable.routesFooter', visibleRoutes.length)}
      </p>
    </div>
  );
}
