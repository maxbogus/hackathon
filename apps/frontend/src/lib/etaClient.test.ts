/**
 * T-129: RED phase — failing tests for the mock/real data client.
 *
 * `etaClient` exposes two pure-async functions: `getStops()` and `getEta(stopId)`.
 * Both must switch between a mock JSON file and a real HTTP fetch based on the
 * `VITE_USE_MOCK` env var. Real-mode points at the backend (T-127 will eventually
 * implement `/api/v1/predictions/eta` and `/api/v1/stops`); mock-mode reads the
 * JSON fixtures under `src/mocks/` directly.
 *
 * We test the client behaviour:
 *  - mock mode: returns the JSON contents (no network)
 *  - real mode: builds the correct URL and rejects when fetch fails
 *  - `getEta(stopId)` returns ETAPrediction[] (the same shape that `recommend()`
 *    consumes — see recommend.ts).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getEta, getStops, type ETAPrediction } from './etaClient';

describe('etaClient', () => {
  beforeEach(() => {
    // vi.stubEnv is the recommended way to override Vite env vars in tests
    // (Vitest 2.x). It mutates import.meta.env via a safe accessor.
    vi.stubEnv('VITE_USE_MOCK', '1');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  describe('getStops()', () => {
    it('returns the mock stops when VITE_USE_MOCK=1', async () => {
      const stops = await getStops();
      expect(stops.length).toBeGreaterThan(0);
      const first = stops[0];
      if (!first) {
        throw new Error('unreachable: stops is non-empty per length assertion');
      }
      expect(first).toHaveProperty('id');
      expect(first).toHaveProperty('name');
      expect(typeof first.name).toBe('string');
    });

    it('returns stops with valid id (positive integer) and non-empty name', async () => {
      const stops = await getStops();
      for (const s of stops) {
        expect(Number.isInteger(s.id)).toBe(true);
        expect(s.id).toBeGreaterThan(0);
        expect(s.name.length).toBeGreaterThan(0);
      }
    });
  });

  describe('getEta()', () => {
    it('returns ETA predictions for a known stop from the mock fixture', async () => {
      const eta = await getEta(1);
      expect(eta.length).toBe(3);
      for (const tram of eta) {
        expect(tram).toHaveProperty('route_id');
        expect(tram).toHaveProperty('route_name');
        expect(tram).toHaveProperty('eta_min');
        expect(tram).toHaveProperty('predicted_load_pct');
        expect(tram).toHaveProperty('model_id');
      }
    });

    it('returns trams sorted by eta_min ascending (closest first)', async () => {
      const eta = await getEta(1);
      for (let i = 1; i < eta.length; i++) {
        const prev = eta[i - 1];
        const curr = eta[i];
        if (prev === undefined || curr === undefined) {
          throw new Error('unreachable: i-1 and i are in bounds');
        }
        expect(curr.eta_min).toBeGreaterThanOrEqual(prev.eta_min);
      }
    });

    it('returns an empty array for an unknown stop id (mock mode is permissive)', async () => {
      const eta = await getEta(999);
      expect(eta).toEqual([]);
    });

    it('returns ETAPrediction objects compatible with recommend() (T-130)', async () => {
      // Smoke-check: the shape returned by getEta() can be fed into recommend()
      // without runtime errors. If this fails we have a contract mismatch.
      const { recommend } = await import('./recommend');
      const eta: ETAPrediction[] = await getEta(1);
      const result = recommend(eta);
      expect(result.severity).toMatch(/^(success|warning|info)$/);
    });

    it('in real mode (VITE_USE_MOCK=0) calls fetch with the documented URL', async () => {
      vi.stubEnv('VITE_USE_MOCK', '0');
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      );

      // We don't have a backend yet, so any network failure must surface as a
      // rejected promise — never silently return [].
      await getEta(1).catch(() => {
        // Expected — mocked fetch may not match real URL on first try.
      });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      const firstCall = fetchSpy.mock.calls[0];
      if (!firstCall) {
        throw new Error('fetch was not called');
      }
      const url = String(firstCall[0]);
      expect(url).toMatch(/\/api\/v1\/predictions\/eta/);
      expect(url).toContain('stop_id=1');
    });

    it('in real mode throws a helpful error when the backend is unreachable', async () => {
      vi.stubEnv('VITE_USE_MOCK', '0');
      vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));

      await expect(getEta(1)).rejects.toThrow(/network down/);
    });
  });
});
