/**
 * T-227/T-122: data layer карты маршрутов.
 *
 * Источник геометрии — `GET /api/v1/geo/routes` (backend, каталог
 * `data/external/stops_routes.json`: 10 маршрутов, 142 остановки).
 * Фронт НЕ читает `data/` напрямую (clinerule 02/08) — только через API.
 *
 * Почему не через Orval-хук: слой повторяет паттерн `lib/routeLoad.ts`
 * (graceful `[]` вместо throw), чтобы карта не ломала дашборд, если
 * backend недоступен или каталог пуст (demo-режим).
 *
 * `mergeRouteTiers()` — мёрж геометрии с загрузкой из `/predictions/load`:
 * цвет на карте = тот же tier, что у prediction-карточек (clinerule 31).
 */

import type { LoadTier } from './loadTier';
import type { RouteLoad } from './routeLoad';

/** Цветовая шкала карты: 4 tier'а загрузки + 'unknown' (нет данных). */
export type MapColorScale = LoadTier | 'unknown';

/** Одна остановка маршрута с координатами (порядок следования — `order`). */
export interface MapStop {
  readonly name: string;
  readonly lat: number;
  readonly lon: number;
  readonly order: number;
}

/** Маршрут = упорядоченный список остановок. */
export interface MapRoute {
  readonly routeId: number;
  readonly stops: readonly MapStop[];
}

/** Результат мёржа геометрии с загрузкой (индексируется по routeId). */
export interface RouteTierIndex {
  readonly tierByRoute: Readonly<Record<number, MapColorScale>>;
  readonly loadPctByRoute: Readonly<Record<number, number>>;
}

interface GeoStopApi {
  name: string;
  lat: number;
  lon: number;
  order: number;
}

interface GeoRouteApi {
  route_id: number;
  n_stops: number;
  stops: GeoStopApi[];
}

interface GeoRoutesApiResponse {
  routes: GeoRouteApi[];
  count: number;
  source: string;
}

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

function buildUrl(path: string): string {
  return `${BASE_URL.replace(/\/$/, '')}${path}`;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function toStops(raw: unknown): MapStop[] {
  if (!Array.isArray(raw)) return [];
  const stops: MapStop[] = [];
  for (const row of raw) {
    if (typeof row !== 'object' || row === null) continue;
    const candidate = row as Partial<GeoStopApi>;
    if (typeof candidate.name !== 'string' || candidate.name === '') continue;
    if (!isFiniteNumber(candidate.lat) || !isFiniteNumber(candidate.lon)) continue;
    stops.push({
      name: candidate.name,
      lat: candidate.lat,
      lon: candidate.lon,
      order: isFiniteNumber(candidate.order) ? candidate.order : stops.length,
    });
  }
  return stops;
}

/**
 * Fetch route geometry from `/api/v1/geo/routes`.
 *
 * Никогда не бросает: любая ошибка (network, 4xx/5xx, битый JSON) → `[]`,
 * дашборд рендерит блок карты без линий.
 */
export async function fetchRouteGeo(signal?: AbortSignal): Promise<MapRoute[]> {
  try {
    const response = await fetch(buildUrl('/geo/routes'), {
      headers: { Accept: 'application/json' },
      signal,
    });
    if (!response.ok) return [];
    const data = (await response.json()) as GeoRoutesApiResponse;
    if (!Array.isArray(data.routes)) return [];

    const routes: MapRoute[] = [];
    for (const raw of data.routes) {
      if (typeof raw !== 'object' || raw === null) continue;
      const candidate = raw as Partial<GeoRouteApi>;
      if (!isFiniteNumber(candidate.route_id)) continue;
      const stops = toStops(candidate.stops);
      if (stops.length === 0) continue;
      routes.push({ routeId: candidate.route_id, stops });
    }
    return routes;
  } catch {
    return [];
  }
}

/**
 * Мёрж геометрии с загрузкой: routeId → tier / load_pct.
 *
 * `unknown` попадает в индекс явно — так карта рисует серую линию вместо
 * «последнего известного» цвета (та же семантика, что у серой карточки).
 */
export function mergeRouteTiers(loads: readonly RouteLoad[]): RouteTierIndex {
  const tierByRoute: Record<number, MapColorScale> = {};
  const loadPctByRoute: Record<number, number> = {};

  for (const load of loads) {
    tierByRoute[load.routeId] = load.tier;
    if (typeof load.loadPct === 'number' && Number.isFinite(load.loadPct)) {
      loadPctByRoute[load.routeId] = load.loadPct;
    }
  }

  return { tierByRoute, loadPctByRoute };
}

/**
 * Центр по всем остановкам (для инициализации карты).
 *
 * Fallback — центр Москвы, если данных нет. Возвращает `[lat, lon]`
 * (координатный порядок JS API/Leaflet по умолчанию — `latlong`).
 */
export function computeCenter(routes: readonly MapRoute[]): [number, number] {
  let latSum = 0;
  let lonSum = 0;
  let count = 0;
  for (const route of routes) {
    for (const stop of route.stops) {
      latSum += stop.lat;
      lonSum += stop.lon;
      count += 1;
    }
  }
  if (count === 0) return [55.751244, 37.618423];
  return [latSum / count, lonSum / count];
}
