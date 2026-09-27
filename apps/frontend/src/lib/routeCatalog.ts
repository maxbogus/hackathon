/**
 * T-233: data layer каталога маршрутов для селектора на экране «Аналитик».
 *
 * Источник — объединение маршрутов, по которым есть данные:
 *   - `GET /api/v1/historical`      → routes с фактическими посадками
 *   - `GET /api/v1/predictions/load` → routes с прогнозами
 *
 * Почему объединение, а не один источник: `/historical` не знает про маршрут 5
 * (в обучающей выборке его нет), а `/predictions/load` не знает про маршруты,
 * которых нет в активном наборе. Аналитик должен видеть все маршруты, для
 * которых на экране вообще есть что показать.
 *
 * Контракт (как у `lib/routeLoad.ts` / `lib/geoRoutes.ts`): функция НИКОГДА не
 * бросает. Один упавший источник не обнуляет список; если оба упали или пусты —
 * возвращаются канонические 10 маршрутов хакатона (F-045 / clinerule 23 R6),
 * чтобы селект никогда не был пустым.
 */

import { fetchPredictionsLoad } from './routeLoad';

/** Канонические 10 маршрутов хакатона (F-045, clinerule 23 R6). */
export const CANONICAL_ROUTES: readonly number[] = [1, 5, 7, 11, 12, 17, 25, 26, 28, 50];

interface HistoricalRoutesApiResponse {
  routes?: unknown;
  count?: unknown;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

function buildUrl(path: string): string {
  return `${BASE_URL.replace(/\/$/, '')}${path}`;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

/** `GET /api/v1/historical` → route_id с хотя бы одним фактом. Ошибка → `[]`. */
async function fetchHistoricalRouteIds(signal?: AbortSignal): Promise<number[]> {
  try {
    const response = await fetch(buildUrl('/historical'), {
      headers: { Accept: 'application/json' },
      signal,
    });
    if (!response.ok) return [];
    const data = (await response.json()) as HistoricalRoutesApiResponse;
    if (!Array.isArray(data.routes)) return [];
    return data.routes.filter(isFiniteNumber);
  } catch {
    return [];
  }
}

/**
 * Список маршрутов для селектора: отсортированное объединение маршрутов из
 * `/historical` и `/predictions/load`, с фолбэком на `CANONICAL_ROUTES`.
 */
export async function fetchRouteCatalog(signal?: AbortSignal): Promise<number[]> {
  const [historical, predictions] = await Promise.all([
    fetchHistoricalRouteIds(signal),
    fetchPredictionsLoad(signal),
  ]);

  const merged = new Set<number>(historical);
  for (const load of predictions) merged.add(load.routeId);

  const sorted = [...merged].sort((a, b) => a - b);
  return sorted.length > 0 ? sorted : [...CANONICAL_ROUTES];
}
