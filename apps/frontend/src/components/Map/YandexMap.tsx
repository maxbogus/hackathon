/**
 * T-122: Yandex-реализация карты (@pbe/react-yandex-maps), lazy-loaded.
 *
 * Включается только когда в env стоит `VITE_MAP_IMPL=yandex` И задан
 * `VITE_YANDEX_MAPS_API_KEY` (см. `mapStrategy.selectMapImpl`). Без ключа
 * показываем notice вместо карты — падать нельзя, демо идёт на OSM.
 *
 * Версия JS API: пакет грузит `api-maps.yandex.ru/2.1/?apikey=...`
 * (`coordorder=latlong` по умолчанию = наш формат `[lat, lon]`).
 *
 * Известное ограничение: приглушение невыбранных маршрутов применяется к
 * линиям (`strokeOpacity`); для точек используется цвет пресета — Yandex
 * не даёт пер-объектную прозрачность так же просто, как Leaflet. Радиус
 * точки тоже задаётся пресетом (`iconCircleRadius` нет в `IPlacemarkOptions`
 * JS API 2.1), поэтому загрузка кодируется цветом + толщиной линии.
 */

import { Map, Placemark, Polyline, YMaps } from '@pbe/react-yandex-maps';

import { getYandexMapsKeyOrNull } from '@/lib/config';
import { computeCenter } from '@/lib/geoRoutes';
import { t, tf } from '@/lib/i18n/t';

import {
  DEFAULT_ZOOM,
  MAP_VIEW_HEIGHT,
  mapColorForTier,
  polylineWeight,
  routeOpacity,
  tierForRoute,
} from './mapColors';
import type { RouteMapProps } from './types';

export default function YandexMap({
  routes,
  tierByRoute,
  loadPctByRoute,
  selectedRouteId = null,
  onSelectRoute,
  height = MAP_VIEW_HEIGHT,
}: RouteMapProps): JSX.Element {
  const apikey = getYandexMapsKeyOrNull();

  if (apikey === null) {
    return (
      <div
        data-testid="route-map-no-key"
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f5f5f5',
          borderRadius: 6,
          color: '#888',
          fontSize: 13,
          padding: 16,
          textAlign: 'center',
        }}
      >
        {t('map.noKey')}
      </div>
    );
  }

  const hasSelection =
    selectedRouteId !== null && routes.some((route) => route.routeId === selectedRouteId);

  return (
    <YMaps query={{ apikey, lang: 'ru_RU' }}>
      <Map
        defaultState={{ center: computeCenter(routes), zoom: DEFAULT_ZOOM }}
        width="100%"
        height={height}
        style={{ borderRadius: 6 }}
      >
        {routes.map((route) => {
          const tier = tierForRoute(tierByRoute, route.routeId);
          const loadPct = loadPctByRoute?.[route.routeId];
          const color = mapColorForTier(tier);
          const isSelected = route.routeId === selectedRouteId;
          const opacity = routeOpacity(isSelected, hasSelection);
          const select = (): void => onSelectRoute?.(route.routeId);

          return (
            <Polyline
              key={`route-${route.routeId}`}
              geometry={route.stops.map((stop): [number, number] => [stop.lat, stop.lon])}
              properties={{ hintContent: tf('map.routeLabel', route.routeId) }}
              options={{
                strokeColor: color,
                strokeWidth: polylineWeight(loadPct),
                strokeOpacity: opacity,
              }}
              onClick={select}
            />
          );
        })}

        {routes.flatMap((route) =>
          route.stops.map((stop) => {
            const color = mapColorForTier(tierForRoute(tierByRoute, route.routeId));
            return (
              <Placemark
                key={`stop-${route.routeId}-${stop.order}`}
                geometry={[stop.lat, stop.lon]}
                properties={{ hintContent: stop.name }}
                options={{
                  preset: 'islands#circleIcon',
                  iconColor: color,
                }}
                onClick={() => onSelectRoute?.(route.routeId)}
              />
            );
          }),
        )}
      </Map>
    </YMaps>
  );
}
