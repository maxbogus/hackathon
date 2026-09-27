/**
 * T-222: тесты для query helper над routeCsv.fetchPredictionsCsv.
 *
 * Helper изолирует URL от consumers и держит единый queryKey, чтобы
 * кэш TanStack Query был консистентным (5 мин) во всех местах
 * (PassengerMode, PredictionsTable, любые будущие интеграции).
 *
 * Mock'аем routeCsv на module level — нам важен контракт "передал signal,
 * получил prediction rows", а не реальный fetch.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchPredictionsCsv } from './routeCsv';
import {
  predictionsCsvQueryKey,
  predictionsCsvQueryFn,
  PREDICTIONS_CSV_STALE_TIME_MS,
} from './predictionsTable';

vi.mock('./routeCsv', () => ({
  fetchPredictionsCsv: vi.fn(),
}));

const mockedFetch = vi.mocked(fetchPredictionsCsv);

afterEach(() => {
  mockedFetch.mockReset();
});

describe('predictionsCsvQueryKey', () => {
  it('стабильная ссылочная идентичность (для TanStack Query)', () => {
    expect(predictionsCsvQueryKey).toEqual(['predictions-csv']);
    // frozen array — accidental mutation в consumer'ах будет видно в dev.
    expect(Object.isFrozen(predictionsCsvQueryKey)).toBe(true);
  });

  it('содержит один сегмент — без параметров (один источник)', () => {
    expect(predictionsCsvQueryKey).toHaveLength(1);
  });
});

describe('predictionsCsvQueryFn', () => {
  it('делегирует в fetchPredictionsCsv', async () => {
    mockedFetch.mockResolvedValueOnce([
      { routeId: 1, date: '2025-11-01', hour: 0, value: 100 },
    ]);
    const rows = await predictionsCsvQueryFn({} as never);
    expect(mockedFetch).toHaveBeenCalledOnce();
    expect(rows).toEqual([
      { routeId: 1, date: '2025-11-01', hour: 0, value: 100 },
    ]);
  });

  it('пробрасывает AbortSignal в fetchPredictionsCsv', async () => {
    mockedFetch.mockResolvedValueOnce([]);
    const ac = new AbortController();
    await predictionsCsvQueryFn({ signal: ac.signal } as never);
    expect(mockedFetch).toHaveBeenCalledWith(ac.signal);
  });

  it('возвращает [] если fetch вернул [] (network/parse error)', async () => {
    mockedFetch.mockResolvedValueOnce([]);
    const rows = await predictionsCsvQueryFn({} as never);
    expect(rows).toEqual([]);
  });
});

describe('PREDICTIONS_CSV_STALE_TIME_MS', () => {
  it('равно 5 минутам (300_000 ms)', () => {
    expect(PREDICTIONS_CSV_STALE_TIME_MS).toBe(5 * 60_000);
  });
});
