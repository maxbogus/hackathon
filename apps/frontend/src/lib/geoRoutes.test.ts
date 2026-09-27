/**
 * T-227/T-122: data-слой карты — парсинг /api/v1/geo/routes и мёрж с загрузкой.
 *
 * Контракт: функция НИКОГДА не бросает (network/HTTP/JSON ошибки → []),
 * иначе падение карты уронило бы весь дашборд «Диспетчер».
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import type { RouteLoad } from './routeLoad';
import { computeCenter, fetchRouteGeo, mergeRouteTiers } from './geoRoutes';

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(payload: unknown, init: { ok?: boolean; throw?: boolean } = {}): void {
  global.fetch = vi.fn(async () => {
    if (init.throw) throw new TypeError('network down');
    return new Response(JSON.stringify(payload), {
      status: init.ok === false ? 500 : 200,
      headers: { 'content-type': 'application/json' },
    });
  }) as typeof global.fetch;
}

function load(partial: Partial<RouteLoad> & { routeId: number }): RouteLoad {
  return {
    boardings: null,
    loadPct: null,
    tier: 'unknown',
    ...partial,
  };
}

describe('fetchRouteGeo', () => {
  it('calls /api/v1/geo/routes and maps snake_case → camelCase', async () => {
    const calls: string[] = [];
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      calls.push(typeof input === 'string' ? input : input.toString());
      return new Response(
        JSON.stringify({
          routes: [
            {
              route_id: 7,
              n_stops: 2,
              stops: [
                { name: 'A', lat: 55.81, lon: 37.73, order: 0 },
                { name: 'B', lat: 55.8, lon: 37.72, order: 1 },
              ],
            },
          ],
          count: 1,
          source: 'external/stops_routes.json',
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      );
    }) as typeof global.fetch;

    const routes = await fetchRouteGeo();

    expect(calls[0]).toBe('/api/v1/geo/routes');
    expect(routes).toHaveLength(1);
    expect(routes[0]?.routeId).toBe(7);
    expect(routes[0]?.stops.map((s) => s.name)).toEqual(['A', 'B']);
    expect(routes[0]?.stops[0]?.lat).toBeCloseTo(55.81);
  });

  it('drops routes without stops and malformed stop rows', async () => {
    mockFetch({
      routes: [
        { route_id: 7, n_stops: 1, stops: [{ name: 'A', lat: 55.8, lon: 37.7, order: 0 }, { name: 'no coords' }] },
        { route_id: 11, n_stops: 0, stops: [] },
        { route_id: null, n_stops: 1, stops: [{ name: 'X', lat: 55.8, lon: 37.7, order: 0 }] },
      ],
      count: 3,
      source: 'x',
    });

    const routes = await fetchRouteGeo();

    expect(routes).toHaveLength(1);
    expect(routes[0]?.stops).toHaveLength(1);
    expect(routes[0]?.stops[0]?.name).toBe('A');
  });

  it('returns [] on HTTP error instead of throwing', async () => {
    mockFetch({ routes: [] }, { ok: false });
    await expect(fetchRouteGeo()).resolves.toEqual([]);
  });

  it('returns [] when the request itself throws', async () => {
    mockFetch({}, { throw: true });
    await expect(fetchRouteGeo()).resolves.toEqual([]);
  });

  it('returns [] when the payload shape is unexpected', async () => {
    mockFetch({ routes: 'nope' });
    await expect(fetchRouteGeo()).resolves.toEqual([]);
  });
});

describe('mergeRouteTiers', () => {
  it('indexes tier by route and keeps load_pct only when numeric', () => {
    const index = mergeRouteTiers([
      load({ routeId: 1, tier: 'green', loadPct: 40 }),
      load({ routeId: 7, tier: 'darkred', loadPct: 130.5 }),
      load({ routeId: 11, tier: 'unknown', loadPct: null }),
    ]);

    expect(index.tierByRoute[1]).toBe('green');
    expect(index.tierByRoute[7]).toBe('darkred');
    expect(index.tierByRoute[11]).toBe('unknown');
    expect(index.loadPctByRoute[7]).toBeCloseTo(130.5);
    expect(index.loadPctByRoute[11]).toBeUndefined();
  });

  it('returns empty indexes for no loads', () => {
    expect(mergeRouteTiers([])).toEqual({ tierByRoute: {}, loadPctByRoute: {} });
  });
});

describe('computeCenter', () => {
  it('averages all stop coordinates', () => {
    expect(
      computeCenter([
        {
          routeId: 1,
          stops: [
            { name: 'A', lat: 55.0, lon: 37.0, order: 0 },
            { name: 'B', lat: 56.0, lon: 38.0, order: 1 },
          ],
        },
      ]),
    ).toEqual([55.5, 37.5]);
  });

  it('falls back to the Moscow centre when there is no geometry', () => {
    expect(computeCenter([])).toEqual([55.751244, 37.618423]);
  });
});
