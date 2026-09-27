/**
 * T-200: data layer for route load grid on PassengerMode.
 */

import { describe, expect, it, vi, afterEach } from 'vitest';

import { fetchAllRouteLoads, fetchRoutesList } from './routeLoad';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fetchRoutesList', () => {
  it('returns the routes array from /api/v1/historical', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ routes: [1, 7, 11, 12, 17], count: 5 }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );

    const result = await fetchRoutesList();
    expect(result).toEqual([1, 7, 11, 12, 17]);
  });

  it('returns [] on 5xx (graceful failure)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('boom', { status: 503 })),
    );
    expect(await fetchRoutesList()).toEqual([]);
  });
});

describe('fetchAllRouteLoads', () => {
  it('maps routes to RouteLoad objects in the same order', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === 'string' ? input : input.toString();
        const m = url.match(/\/api\/v1\/historical\/(\d+)/);
        if (!m) return new Response('not found', { status: 404 });
        const rid = Number(m[1]);
        const valueByRoute: Record<number, number> = { 1: 60, 7: 150, 11: 200 };
        return new Response(
          JSON.stringify({
            route_id: rid,
            granularity: 'hour',
            points: [{ period_start: '2025-09-30T20:00:00Z', value: valueByRoute[rid] ?? 0 }],
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }),
    );

    const result = await fetchAllRouteLoads([1, 7, 11]);
    expect(result.map((r) => r.routeId)).toEqual([1, 7, 11]);
    // 60/150 = 40 → green
    expect(result[0]?.loadPct).toBeCloseTo(40, 1);
    expect(result[0]?.tier).toBe('green');
    // 150/150 = 100 → red
    expect(result[1]?.loadPct).toBeCloseTo(100, 1);
    expect(result[1]?.tier).toBe('red');
    // 200/150 = 133.3 → darkred
    expect(result[2]?.loadPct).toBeCloseTo(133.3, 1);
    expect(result[2]?.tier).toBe('darkred');
  });

  it('returns tier=unknown for routes with no points', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({ route_id: 7, granularity: 'hour', points: [] }),
          { status: 200 },
        ),
      ),
    );

    const result = await fetchAllRouteLoads([7]);
    expect(result[0]?.tier).toBe('unknown');
    expect(result[0]?.loadPct).toBeNull();
  });

  it('returns tier=unknown when fetch throws', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('network down');
      }),
    );

    const result = await fetchAllRouteLoads([1, 7]);
    expect(result.every((r) => r.tier === 'unknown')).toBe(true);
  });
});
