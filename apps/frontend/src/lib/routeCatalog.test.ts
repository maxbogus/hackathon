/**
 * T-233: data layer каталога маршрутов для селектора на экране «Аналитик».
 *
 * Источник — объединение двух endpoint'ов, по которым есть данные:
 *   - GET /api/v1/historical      → { routes: number[], count }
 *   - GET /api/v1/predictions/load → { loads: [{ route_id, ... }], count }
 *
 * Контракт (как у lib/routeLoad.ts / lib/geoRoutes.ts): функция НИКОГДА не
 * бросает. Если оба источника недоступны или пусты — возвращаются
 * канонические 10 маршрутов хакатона (F-045 / clinerule 23 R6).
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { CANONICAL_ROUTES, fetchRouteCatalog } from './routeCatalog';

afterEach(() => {
  vi.restoreAllMocks();
});

interface MockOptions {
  readonly historical?: unknown;
  readonly historicalStatus?: number;
  readonly loads?: unknown;
  readonly loadsStatus?: number;
}

/**
 * fetch-мок: `/historical/load` проверяется РАНЬШЕ `/historical`, потому что
 * подстроки пересекаются (`/api/v1/historical` ⊂ `/api/v1/historical/load`).
 */
function mockApi(options: MockOptions = {}): void {
  const {
    historical = { routes: [], count: 0 },
    historicalStatus = 200,
    loads = { loads: [], count: 0 },
    loadsStatus = 200,
  } = options;

  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString();
      const json = (payload: unknown, status: number): Response =>
        new Response(JSON.stringify(payload), {
          status,
          headers: { 'content-type': 'application/json' },
        });

      if (url.includes('/historical/load')) return json({ loads: [], count: 0 }, 200);
      if (url.includes('/predictions/load')) return json(loads, loadsStatus);
      if (url.includes('/historical')) return json(historical, historicalStatus);
      return new Response('not found', { status: 404 });
    }),
  );
}

describe('fetchRouteCatalog', () => {
  it('returns the sorted union of historical and prediction routes', async () => {
    mockApi({
      historical: { routes: [17, 1, 7], count: 3 },
      loads: {
        loads: [
          { route_id: 7, boardings_avg: 120, load_pct: 80, tier: 'yellow' },
          { route_id: 25, boardings_avg: 60, load_pct: 40, tier: 'green' },
        ],
        count: 2,
      },
    });

    await expect(fetchRouteCatalog()).resolves.toEqual([1, 7, 17, 25]);
  });

  it('drops non-numeric entries coming from /historical', async () => {
    mockApi({
      historical: { routes: [7, null, 'x', Number.NaN, 1] },
      loads: { loads: [], count: 0 },
    });

    await expect(fetchRouteCatalog()).resolves.toEqual([1, 7]);
  });

  it('still returns routes when one source fails (historical 500)', async () => {
    mockApi({
      historicalStatus: 500,
      loads: { loads: [{ route_id: 5, boardings_avg: 10, load_pct: 7, tier: 'green' }] },
    });

    await expect(fetchRouteCatalog()).resolves.toEqual([5]);
  });

  it('still returns routes when one source fails (predictions 503)', async () => {
    mockApi({
      historical: { routes: [7] },
      loadsStatus: 503,
      loads: { detail: 'boom' },
    });

    await expect(fetchRouteCatalog()).resolves.toEqual([7]);
  });

  it('falls back to CANONICAL_ROUTES when both sources are empty', async () => {
    mockApi();

    await expect(fetchRouteCatalog()).resolves.toEqual([...CANONICAL_ROUTES]);
  });

  it('falls back to CANONICAL_ROUTES when the network throws', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('network down');
      }),
    );

    await expect(fetchRouteCatalog()).resolves.toEqual([...CANONICAL_ROUTES]);
  });

  it('exposes the canonical hackathon routes (F-045)', () => {
    expect([...CANONICAL_ROUTES]).toEqual([1, 5, 7, 11, 12, 17, 25, 26, 28, 50]);
  });
});
