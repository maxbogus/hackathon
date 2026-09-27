/**
 * T-122: публичный контракт карты маршрутов (props) + ре-экспорт типов данных.
 *
 * Реализации (`LeafletMap`, `YandexMap`) обязаны принимать ровно этот набор
 * props — тогда переключение провайдера через env не меняет вызывающий код.
 * Типы данных живут в `lib/geoRoutes.ts` (data-слой), здесь только их ре-экспорт.
 */

import type { MapColorScale, MapRoute } from '@/lib/geoRoutes';

export type { MapColorScale, MapRoute, MapStop } from '@/lib/geoRoutes';

export interface RouteMapProps {
  /** Геометрия маршрутов (из GET /api/v1/geo/routes). */
  readonly routes: readonly MapRoute[];
  /** routeId → tier загрузки (из /predictions/load), цвет линии/точек. */
  readonly tierByRoute?: Readonly<Record<number, MapColorScale>>;
  /** routeId → load_pct (из /predictions/load), толщина линии/радиус точек. */
  readonly loadPctByRoute?: Readonly<Record<number, number>>;
  /** Выбранный маршрут (подсвечен, остальные приглушены). null = нет выбора. */
  readonly selectedRouteId?: number | null;
  /** Клик по маршруту/остановке на карте. */
  readonly onSelectRoute?: (routeId: number) => void;
  /** Высота карты в px (по умолчанию MAP_VIEW_HEIGHT). */
  readonly height?: number;
}
