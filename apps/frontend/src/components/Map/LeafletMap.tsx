/**
 * T-122: OSM-реализация карты (Leaflet + react-leaflet), lazy-loaded.
 *
 * Почему Leaflet: работает без ключей и без внешних аккаунтов (D-003) —
 * дефолт проекта, демо не зависит от валидности ключа Яндекс.Карт.
 *
 * Что рисуем (ТЗ §3.1.4):
 *   - линия маршрута через остановки в порядке `order`, толщина ∝ load_pct;
 *   - точки остановок (CircleMarker) того же цвета, tooltip = название;
 *   - клик по линии/точке → `onSelectRoute` (синхронизация с карточками).
 *
 * CircleMarker (а не Marker) выбран намеренно: не требует image-ассетов
 * leaflet (`marker-icon.png`), которые ломаются в сборках/тестах.
 */

import { Fragment, useEffect } from 'react';
import L from 'leaflet';
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

import { tf } from '@/lib/i18n/t';

import {
  DEFAULT_ZOOM,
  MAP_VIEW_HEIGHT,
  MOSCOW_CENTER,
  SELECTED_ZOOM,
  mapColorForTier,
  polylineWeight,
  routeOpacity,
  stopRadius,
  tierForRoute,
} from './mapColors';
import type { MapRoute, MapStop, RouteMapProps } from './types';

interface FitToProps {
  readonly routes: readonly MapRoute[];
  readonly selectedRouteId: number | null;
}

/** Подгоняет вид: под выбранный маршрут, либо под все сразу (если выбора нет). */
function FitToSelection({ routes, selectedRouteId }: FitToProps): null {
  const map = useMap();

  useEffect(() => {
    const selected =
      selectedRouteId === null
        ? undefined
        : routes.find((route) => route.routeId === selectedRouteId);
    const stops: readonly MapStop[] = selected ? selected.stops : routes.flatMap((r) => r.stops);
    if (stops.length < 2) return;
    const bounds = L.latLngBounds(stops.map((s): [number, number] => [s.lat, s.lon]));
    map.fitBounds(bounds, {
      padding: [24, 24],
      maxZoom: selected ? SELECTED_ZOOM : DEFAULT_ZOOM,
    });
  }, [map, routes, selectedRouteId]);

  return null;
}

export default function LeafletMap({
  routes,
  tierByRoute,
  loadPctByRoute,
  selectedRouteId = null,
  onSelectRoute,
  height = MAP_VIEW_HEIGHT,
}: RouteMapProps): JSX.Element {
  const hasSelection =
    selectedRouteId !== null && routes.some((route) => route.routeId === selectedRouteId);

  return (
    <MapContainer
      center={MOSCOW_CENTER}
      zoom={DEFAULT_ZOOM}
      style={{ height, width: '100%', borderRadius: 6 }}
      scrollWheelZoom
    >
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap"
      />
      <FitToSelection routes={routes} selectedRouteId={hasSelection ? selectedRouteId : null} />

      {routes.map((route) => {
        const tier = tierForRoute(tierByRoute, route.routeId);
        const loadPct = loadPctByRoute?.[route.routeId];
        const color = mapColorForTier(tier);
        const isSelected = route.routeId === selectedRouteId;
        const opacity = routeOpacity(isSelected, hasSelection);
        const positions = route.stops.map((stop): [number, number] => [stop.lat, stop.lon]);
        const select = (): void => onSelectRoute?.(route.routeId);

        return (
          <Fragment key={route.routeId}>
            <Polyline
              positions={positions}
              pathOptions={{
                color,
                weight: polylineWeight(loadPct),
                opacity,
                lineCap: 'round',
              }}
              eventHandlers={{ click: select }}
            >
              <Tooltip>{tf('map.routeLabel', route.routeId)}</Tooltip>
            </Polyline>

            {route.stops.map((stop) => (
              <CircleMarker
                key={`${route.routeId}-${stop.order}`}
                center={[stop.lat, stop.lon]}
                radius={stopRadius(loadPct)}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: 0.9 * opacity,
                  opacity,
                }}
                eventHandlers={{ click: select }}
              >
                <Tooltip>{stop.name}</Tooltip>
              </CircleMarker>
            ))}
          </Fragment>
        );
      })}
    </MapContainer>
  );
}
