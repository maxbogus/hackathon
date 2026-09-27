/**
 * T-226: TanStack Query helper над routeCsv.fetchActualsCsv.
 *
 * Зеркало predictionsTable.ts (T-222) — изолирует URL и queryKey от consumers,
 * чтобы кэш был консистентным во всех местах (HistoricalView, HistoricalTable,
 * будущие интеграции).
 *
 * Контракт: 5 минут staleTime (R6 SLA хакатона, см. clinerule-08).
 * Данные actuals меняются только при новом train run (MAX 1-2 раз в день),
 * 5 минут — частый refresh не нужен.
 *
 * Usage:
 *   const { data, isLoading, error } = useQuery({
 *     queryKey: historicalCsvQueryKey,
 *     queryFn: historicalCsvQueryFn,
 *     staleTime: HISTORICAL_CSV_STALE_TIME_MS,
 *   });
 */

import type { QueryFunctionContext } from '@tanstack/react-query';

import { fetchActualsCsv } from './routeCsv';
import type { PredictionRow } from './routeCsv';

/**
 * Стабильная ссылочная идентичность queryKey — frozen, чтобы случайный
 * mutation в consumer'ах не ломал кэш. Frozen массив держит isEqual ===
 * true для всех вызовов (TanStack Query structural compare).
 *
 * Отличается от predictionsCsvQueryKey (['predictions-csv']), чтобы
 * predictions и historicals кэшировались независимо — они могут
 * расходиться (actuals в БД ≠ predictions в submission.csv).
 */
export const historicalCsvQueryKey: readonly ['historical-csv'] = Object.freeze([
  'historical-csv',
]);

/**
 * Тип QueryFunctionContext у TanStack Query v5 — у нас один сегмент без params,
 * сигнал пробрасывается в fetch для cancellation на unmount.
 */
type HistoricalCsvContext = QueryFunctionContext<typeof historicalCsvQueryKey>;

/**
 * Query function. Делегирует в fetchActualsCsv, отдавая ответ как есть
 * (включая [] при ошибке — caller's responsibility показать Alert).
 *
 * PredictionRow == ActualRow (один тип для одной формы, см. routeCsv.ts).
 */
export async function historicalCsvQueryFn(
  ctx: HistoricalCsvContext,
): Promise<PredictionRow[]> {
  return fetchActualsCsv(ctx.signal);
}

/**
 * 5 минут — оптимально для исторических данных (CSV меняется только при
 * новом train run, не чаще 1-2 раз/день). См. R6 SLA (p95 ≤ 2s) — чаще
 * перезагружать нет смысла, нагрузка на API не нужна.
 */
export const HISTORICAL_CSV_STALE_TIME_MS = 5 * 60_000;
