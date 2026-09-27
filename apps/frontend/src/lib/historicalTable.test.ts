/**
 * T-226: тесты для query helper над routeCsv.fetchActualsCsv.
 *
 * Зеркало predictionsTable.test.ts — изолирует URL от consumers и держит
 * единый queryKey, чтобы кэш TanStack Query был консистентным (5 мин)
 * во всех местах (HistoricalView, HistoricalTable, будущие интеграции).
 *
 * Mock'аем routeCsv на module level — нам важен контракт "передал signal,
 * получил actual rows", а не реальный fetch.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchActualsCsv } from './routeCsv';
import {
  historicalCsvQueryKey,
  historicalCsvQueryFn,
  HISTORICAL_CSV_STALE_TIME_MS,
} from './historicalTable';

vi.mock('./routeCsv', () => ({
  fetchActualsCsv: vi.fn(),
}));

const mockedFetch = vi.mocked(fetchActualsCsv);

afterEach(() => {
  mockedFetch.mockReset();
});

describe('historicalCsvQueryKey', () => {
  it('стабильная ссылочная идентичность (для TanStack Query)', () => {
    expect(historicalCsvQueryKey).toEqual(['historical-csv']);
    // frozen array — accidental mutation в consumer'ах будет видно в dev.
    expect(Object.isFrozen(historicalCsvQueryKey)).toBe(true);
  });

  it('содержит один сегмент — без параметров (один источник)', () => {
    expect(historicalCsvQueryKey).toHaveLength(1);
  });

  it('отличается от predictionsCsvQueryKey (разные queryKeys)', () => {
    // dynamic import чтобы избежать circular issue на mock setup
    return import('./predictionsTable').then(({ predictionsCsvQueryKey }) => {
      expect(historicalCsvQueryKey).not.toEqual(predictionsCsvQueryKey);
    });
  });
});

describe('historicalCsvQueryFn', () => {
  it('делегирует в fetchActualsCsv', async () => {
    mockedFetch.mockResolvedValueOnce([
      { routeId: 1, date: '2025-10-31', hour: 0, value: 500 },
    ]);
    const rows = await historicalCsvQueryFn({} as never);
    expect(mockedFetch).toHaveBeenCalledOnce();
    expect(rows).toEqual([
      { routeId: 1, date: '2025-10-31', hour: 0, value: 500 },
    ]);
  });

  it('пробрасывает AbortSignal в fetchActualsCsv', async () => {
    mockedFetch.mockResolvedValueOnce([]);
    const ac = new AbortController();
    await historicalCsvQueryFn({ signal: ac.signal } as never);
    expect(mockedFetch).toHaveBeenCalledWith(ac.signal);
  });

  it('возвращает [] если fetch вернул [] (network/parse error)', async () => {
    mockedFetch.mockResolvedValueOnce([]);
    const rows = await historicalCsvQueryFn({} as never);
    expect(rows).toEqual([]);
  });
});

describe('HISTORICAL_CSV_STALE_TIME_MS', () => {
  it('равно 5 минутам (300_000 ms)', () => {
    expect(HISTORICAL_CSV_STALE_TIME_MS).toBe(5 * 60_000);
  });
});
