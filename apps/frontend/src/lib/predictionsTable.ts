/**
 * T-222: TanStack Query helper над routeCsv.fetchPredictionsCsv.
 *
 * Изолирует URL и queryKey от consumers, чтобы кэш был консистентным
 * во всех местах (PassengerMode, PredictionsTable, будущие интеграции).
 *
 * Контракт: 5 минут staleTime (R6 SLA хакатона, см. clinerule-08).
 * Данные обновляются только при новом submission (MAX 1-2 раз в день),
 * 5 минут — частый refresh не нужен.
 *
 * Usage:
 *   const { data, isLoading, error } = useQuery({
 *     queryKey: predictionsCsvQueryKey,
 *     queryFn: predictionsCsvQueryFn,
 *     staleTime: PREDICTIONS_CSV_STALE_TIME_MS,
 *   });
 */

import type { QueryFunctionContext } from '@tanstack/react-query';

import { fetchPredictionsCsv } from './routeCsv';
import type { PredictionRow } from './routeCsv';

/**
 * Стабильная ссылочная идентичность queryKey — frozen, чтобы случайный
 * mutation в consumer'ах не ломал кэш. Frozen массив держит isEqual ===
 * true для всех вызовов (TanStack Query structural compare).
 */
export const predictionsCsvQueryKey: readonly ['predictions-csv'] = Object.freeze([
  'predictions-csv',
]);

/**
 * Тип QueryFunctionContext у TanStack Query v5 — у нас один сегмент без params,
 * сигнал пробрасывается в fetch для cancellation на unmount.
 */
type PredictionsCsvContext = QueryFunctionContext<typeof predictionsCsvQueryKey>;

/**
 * Query function. Делегирует в fetchPredictionsCsv, отдавая ответ
 * как есть (включая [] при ошибке — caller's responsibility показать Alert).
 */
export async function predictionsCsvQueryFn(
  ctx: PredictionsCsvContext,
): Promise<PredictionRow[]> {
  return fetchPredictionsCsv(ctx.signal);
}

/**
 * 5 минут — оптимально для прогнозов (CSV меняется редко, не чаще 1-2 раз/день).
 * См. R6 SLA (p95 ≤ 2s) — чаще перезагружать нет смысла, нагрузка на API не нужна.
 */
export const PREDICTIONS_CSV_STALE_TIME_MS = 5 * 60_000;
