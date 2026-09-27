/**
 * T-218: data layer для пассажирского экрана.
 *
 * PassengerMode показывает ДВА блока:
 *  - "Как было" (actuals)     — GET /api/v1/historical/load
 *  - "Как будет" (predictions) — GET /api/v1/predictions/load
 *
 * См. clinerule 31 (apps/frontend/src/lib/i18n/MIGRATION.md).
 *
 * Параллельные fetch через Promise.all (R6 SLA — все маршруты за <2с).
 *
 * Возвращает `null` loadPct для маршрута если:
 *  - fetch упал
 *  - endpoint вернул пустой список
 * UI рендерит такие карточки как «нет данных» (tier: unknown, текст «—»).
 */

import { loadTier, type LoadTier } from './loadTier';

export const DEFAULT_TRAM_CAPACITY = 150;

export type RouteLoadVariant = 'actual' | 'prediction';

export interface RouteLoad {
  readonly routeId: number;
  /** Raw boardings_avg из endpoint. */
  readonly boardings: number | null;
  /** Computed load_pct (boardings / TRAM_CAPACITY × 100). */
  readonly loadPct: number | null;
  /** Severity tier (green/yellow/red/darkred) or 'unknown' if no data. */
  readonly tier: LoadTier | 'unknown';
  /** Количество точек, использованных для среднего (доверие). */
  readonly sampleSize?: number;
  /** Последний timestamp данных (для подписи «обновлено ...»). */
  readonly periodEnd?: string | null;
}

interface RouteLoadApiItem {
  route_id: number;
  boardings_avg: number;
  load_pct: number;
  tier: LoadTier;
  sample_size?: number;
  period_start?: string | null;
  period_end?: string | null;
}

interface RouteLoadApiResponse {
  loads: RouteLoadApiItem[];
  count: number;
  source: string;
  from_date?: string | null;
  to_date?: string | null;
  used_fallback?: boolean;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

function buildUrl(path: string): string {
  // Orval сгенерил без /api, customInstance добавит через BASE_URL
  return `${BASE_URL.replace(/\/$/, '')}${path}`;
}

async function fetchLoadSummary(
  path: string,
  signal?: AbortSignal,
): Promise<RouteLoad[]> {
  try {
    const response = await fetch(buildUrl(path), {
      headers: { Accept: 'application/json' },
      signal,
    });
    if (!response.ok) {
      return [];
    }
    const data = (await response.json()) as RouteLoadApiResponse;
    if (!Array.isArray(data.loads) || data.loads.length === 0) {
      return [];
    }
    return data.loads.map((item) => ({
      routeId: item.route_id,
      boardings: typeof item.boardings_avg === 'number' ? item.boardings_avg : null,
      loadPct: typeof item.load_pct === 'number' ? item.load_pct : null,
      tier: item.tier,
      sampleSize: item.sample_size,
      periodEnd: item.period_end ?? null,
    }));
  } catch {
    return [];
  }
}

/**
 * Fetch avg boardings per route from /api/v1/historical/load.
 * Block 'kak bylo' for PassengerMode.
 */
export async function fetchActualsLoad(
  signal?: AbortSignal,
): Promise<RouteLoad[]> {
  return fetchLoadSummary('/historical/load', signal);
}

/**
 * Fetch avg predictions per route from /api/v1/predictions/load.
 * Block 'kak budet' for PassengerMode.
 */
export async function fetchPredictionsLoad(
  signal?: AbortSignal,
): Promise<RouteLoad[]> {
  return fetchLoadSummary('/predictions/load', signal);
}

/**
 * Fetch both blocks in parallel. Returns in the SAME order as input.
 * T-218: replaces fetchAllRouteLoads which used /historical/{route_id}.
 */
export async function fetchAllRouteLoads(
  signal?: AbortSignal,
): Promise<{ actuals: RouteLoad[]; predictions: RouteLoad[] }> {
  const [actuals, predictions] = await Promise.all([
    fetchActualsLoad(signal),
    fetchPredictionsLoad(signal),
  ]);
  return { actuals, predictions };
}

// Re-export for backward-compat (tests)
export { loadTier };
export type { LoadTier };
