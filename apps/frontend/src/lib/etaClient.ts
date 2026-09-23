/**
 * T-129: data layer for the passenger-mode UI.
 *
 * Two async functions exposed to React:
 *   - `getStops()` returns the list of tram stops
 *   - `getEta(stopId)` returns the next few trams arriving at a stop
 *
 * Each one routes between a mock JSON fixture (used during MVP development,
 * the demo, and the unit tests) and the real backend (T-127 will eventually
 * implement `/api/v1/predictions/eta`). The switch is driven by the Vite env
 * var `VITE_USE_MOCK`:
 *
 *   VITE_USE_MOCK=1  → read from src/mocks/*.json
 *   VITE_USE_MOCK=0  → fetch from the backend (via Vite proxy in dev)
 *
 * Why a thin client wrapper instead of importing the mocks directly?
 *  - Components stay decoupled from the storage format
 *  - Switching to real data later is a one-character config change
 *  - Easy to mock in tests via `vi.mock('@/lib/etaClient', ...)`
 */

import type { ETAPrediction } from './recommend';
export type { ETAPrediction };

import stopsFixture from '@/mocks/stops.json';
import etaFixture from '@/mocks/eta_predictions.json';

/** A public-transport stop with its geographical coordinates. */
export interface Stop {
  id: number;
  name: string;
  lat: number;
  lon: number;
  /** Route ids/labels that call at this stop (e.g. [7, 9, "А"]). */
  routes: ReadonlyArray<number | string>;
}

/**
 * True when we should serve data from local fixtures.
 * Defaults to mock mode so a fresh checkout works without a backend.
 */
function isMockMode(): boolean {
  const value = import.meta.env.VITE_USE_MOCK;
  // Treat anything other than '0' / 'false' as mock-on. This is the
  // convention used by Vite/Vitest, and is robust to the env being unset.
  return value !== '0' && value !== 'false';
}

/**
 * Fetch the list of tram stops. In mock mode this returns the fixture
 * synchronously (wrapped in a Promise so the call sites are uniform).
 */
export async function getStops(): Promise<Stop[]> {
  if (isMockMode()) {
    // Cast: stops.json is a frozen readonly array of Stop-shaped objects.
    return stopsFixture as Stop[];
  }
  const response = await fetch('/api/v1/stops');
  if (!response.ok) {
    throw new Error(`getStops: HTTP ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as Stop[];
}

/**
 * Fetch the next N upcoming trams for a given stop.
 *
 * The real backend contract (post-T-127) is
 *   GET /api/v1/predictions/eta?stop_id={stopId}&n={n}
 *
 * In mock mode we read from `eta_predictions.json`, keyed by stop_id.
 * Unknown stops return [] rather than throwing — the UI treats an empty
 * list as "no data" via recommend().
 */
export async function getEta(stopId: number, _n = 3): Promise<ETAPrediction[]> {
  if (isMockMode()) {
    const key = String(stopId);
    const record = etaFixture as Record<string, ETAPrediction[] | undefined>;
    const list = record[key] ?? [];
    // Sort defensively even though the fixture is already in order — keeps
    // the contract obvious for anyone reading the code.
    return [...list].sort((a, b) => a.eta_min - b.eta_min);
  }

  const url = `/api/v1/predictions/eta?stop_id=${encodeURIComponent(String(stopId))}&n=${encodeURIComponent(String(_n))}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`getEta(${stopId}): HTTP ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as ETAPrediction[];
}
