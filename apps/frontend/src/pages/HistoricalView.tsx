/**
 * T-226: страница-обёртка над <HistoricalTable>.
 *
 * Ответственность:
 *  - Дёрнуть /api/v1/historical/export.csv через TanStack Query
 *    (helper lib/historicalTable.ts).
 *  - Передать rows / isLoading / error в HistoricalTable.
 *
 * Компонент HistoricalTable остаётся pure UI (D-038.1) — этот файл
 * единственное место, где встречается "fetch + React component".
 *
 * Зеркало PredictionsView.tsx, но без блока активной модели (исторические
 * данные не привязаны к конкретной ML-модели — это факт из БД).
 */

import { useQuery } from '@tanstack/react-query';

import { t } from '@/lib/i18n/t';
import { HistoricalTable } from '@/components/Passenger';
import {
  historicalCsvQueryFn,
  historicalCsvQueryKey,
  HISTORICAL_CSV_STALE_TIME_MS,
} from '@/lib/historicalTable';

export function HistoricalView(): JSX.Element {
  // 5-min cached query (clinerule D-038.2 / R6 SLA).
  const { data, isLoading, error } = useQuery({
    queryKey: historicalCsvQueryKey,
    queryFn: historicalCsvQueryFn,
    staleTime: HISTORICAL_CSV_STALE_TIME_MS,
  });

  const rows = data ?? [];
  const errMessage = error
    ? error instanceof Error
      ? error.message
      : String(error)
    : null;

  return (
    <main
      data-testid="historical-view"
      style={{
        padding: '16px 24px',
        maxWidth: 1400,
        margin: '0 auto',
      }}
    >
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>{t('historical.viewTitle')}</h1>
        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 13 }}>
          {t('historical.viewHint')}
        </p>
      </header>

      <HistoricalTable rows={rows} isLoading={isLoading} error={errMessage} />
    </main>
  );
}
