/**
 * T-200 (новая редакция): data layer для пассажирского экрана.
 *
 * Получает список маршрутов из /api/v1/historical, потом для каждого — последний
 * час из /api/v1/historical/{route_id}?granularity=hour. Переводит `value`
 * (boardings) в `load_pct` делением на TRAM_CAPACITY (default 150, см.
 * `apps/backend/app/forecast/load.py` — DEFAULT_TRAM_CAPACITY = 150).
 *
 * Параллельные fetch через Promise.all (R6 SLA — все маршруты за <2с).
 *
 * Возвращает `null` для маршрута если:
 *  - fetch упал
 *  - backend вернул 0 points (нет данных за выбранный час)
 * UI рендерит такие карточки как «нет данных» (tier: unknown, текст «—»).
 */

import type { LoadTier } from './loadTier';
import { loadTier } from './loadTier';

export const DEFAULT_TRAM_CAPACITY = 150;

export interface RouteLoad {
  readonly routeId: number;
  /** Raw boardings count from /api/v1/historical. */
  readonly boardings: number | null;
  /** Computed load_pct (boardings / TRAM_CAPACITY × 100). */
  readonly loadPct: number | null;
  /** Severity tier (green/yellow/red/darkred) or 'unknown' if no data. */
  readonly tier: LoadTier | 'unknown';
}

interface RoutesListResponse {
  routes: number[];
  count: number;
}

interface HistoricalPoint {
  period_start: string;
  period_end: string;
  value: number;
}

interface HistoricalResponse {
  route_id: number;
  granularity: string;
  points: HistoricalPoint[];
}

/**
 * Fetch all route IDs available on the server (today's data).
 */
export async function fetchRoutesList(
  baseUrl = '/api/v1/historical',
): Promise<number[]> {
  const response = await fetch(baseUrl, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as RoutesListResponse;
  return Array.isArray(data.routes) ? data.routes : [];
}

/**
 * Fetch the latest hourly historical data point for a single route.
 * Returns null if no points or HTTP failure.
 */
async function fetchLatestRouteLoad(
  routeId: number,
  baseUrl = '/api/v1/historical',
  capacity: number = DEFAULT_TRAM_CAPACITY,
): Promise<RouteLoad> {
  try {
    // No from/to → backend returns latest available data
    const response = await fetch(
      `${baseUrl}/${routeId}?granularity=hour`,
      { headers: { Accept: 'application/json' } },
    );
    if (!response.ok) {
      return { routeId, boardings: null, loadPct: null, tier: 'unknown' };
    }
    const data = (await response.json()) as HistoricalResponse;
    if (!Array.isArray(data.points) || data.points.length === 0) {
      return { routeId, boardings: null, loadPct: null, tier: 'unknown' };
    }
    // Last point = most recent hour
    const last = data.points[data.points.length - 1];
    const value = typeof last?.value === 'number' ? last.value : 0;
    const loadPct = capacity > 0 ? (value / capacity) * 100 : 0;
    return {
      routeId,
      boardings: value,
      loadPct,
      tier: loadTier(loadPct),
    };
  } catch {
    return { routeId, boardings: null, loadPct: null, tier: 'unknown' };
  }
}

/**
 * Fetch latest load for all routes in parallel.
 * Returns array in the SAME order as input routeIds.
 * Failed fetches return RouteLoad with tier='unknown'.
 */
export async function fetchAllRouteLoads(
  routeIds: readonly number[],
  baseUrl = '/api/v1/historical',
  capacity: number = DEFAULT_TRAM_CAPACITY,
): Promise<RouteLoad[]> {
  return Promise.all(
    routeIds.map((rid) => fetchLatestRouteLoad(rid, baseUrl, capacity)),
  );
}
