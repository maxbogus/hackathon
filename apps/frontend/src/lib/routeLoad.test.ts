/**
 * T-218: data layer for PassengerMode — два summary endpoint.
 *
 * Поведение:
 *  - fetchActualsLoad() → GET /api/v1/historical/load
 *  - fetchPredictionsLoad() → GET /api/v1/predictions/load
 *  - оба возвращают [] при network errors
 */

import { describe, expect, it, vi, afterEach } from 'vitest';

import {
  fetchAllRouteLoads,
  fetchActualsLoad,
  fetchPredictionsLoad,
} from './routeLoad';

afterEach(() => {
  vi.restoreAllMocks();
});

function mockSummary(url: string, payload: unknown, status = 200): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const u = typeof input === 'string' ? input : input.toString();
      if (u.includes(url)) {
        return new Response(JSON.stringify(payload), {
          status,
          headers: { 'content-type': 'application/json' },
        });
      }
      return new Response('not found', { status: 404 });
    }),
  );
}

describe('fetchActualsLoad', () => {
  it('returns parsed RouteLoad[] from /api/v1/historical/load', async () => {
    mockSummary('/api/v1/historical/load', {
      loads: [
        {
          route_id: 1,
          boardings_avg: 80,
          load_pct: 53.33,
          tier: 'green',
          sample_size: 24,
          period_start: '2025-10-30T00:00:00Z',
          period_end: '2025-10-30T23:00:00Z',
        },
        {
          route_id: 7,
          boardings_avg: 120,
          load_pct: 80,
          tier: 'yellow',
          sample_size: 24,
        },
      ],
      count: 2,
      source: 'actuals',
      used_fallback: true,
    });
    const result = await fetchActualsLoad();
    expect(result).toHaveLength(2);
    expect(result[0]).toMatchObject({
      routeId: 1,
      boardings: 80,
      loadPct: 53.33,
      tier: 'green',
      sampleSize: 24,
    });
  });

  it('returns [] on 5xx (graceful failure)', async () => {
    mockSummary('/api/v1/historical/load', { detail: 'boom' }, 503);
    expect(await fetchActualsLoad()).toEqual([]);
  });

  it('returns [] on network error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('net'); }));
    expect(await fetchActualsLoad()).toEqual([]);
  });
});

describe('fetchPredictionsLoad', () => {
  it('returns parsed RouteLoad[] from /api/v1/predictions/load', async () => {
    mockSummary('/api/v1/predictions/load', {
      loads: [
        {
          route_id: 1,
          boardings_avg: 60,
          load_pct: 40,
          tier: 'green',
          sample_size: 720,
        },
      ],
      count: 1,
      source: 'predictions',
    });
    const result = await fetchPredictionsLoad();
    expect(result).toHaveLength(1);
    expect(result[0]?.tier).toBe('green');
  });

  it('returns [] on 4xx', async () => {
    mockSummary('/api/v1/predictions/load', { detail: 'bad' }, 400);
    expect(await fetchPredictionsLoad()).toEqual([]);
  });
});

describe('fetchAllRouteLoads (T-218: parallel)', () => {
  it('returns {actuals, predictions} from two parallel fetches', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const u = typeof input === 'string' ? input : input.toString();
        if (u.includes('/historical/load')) {
          return new Response(
            JSON.stringify({
              loads: [{ route_id: 1, boardings_avg: 50, load_pct: 33, tier: 'green', sample_size: 24 }],
              count: 1,
              source: 'actuals',
            }),
            { status: 200, headers: { 'content-type': 'application/json' } },
          );
        }
        if (u.includes('/predictions/load')) {
          return new Response(
            JSON.stringify({
              loads: [{ route_id: 1, boardings_avg: 70, load_pct: 46, tier: 'green', sample_size: 24 }],
              count: 1,
              source: 'predictions',
            }),
            { status: 200, headers: { 'content-type': 'application/json' } },
          );
        }
        return new Response('not found', { status: 404 });
      }),
    );
    const result = await fetchAllRouteLoads();
    expect(result.actuals[0]?.boardings).toBe(50);
    expect(result.predictions[0]?.boardings).toBe(70);
  });
});
