/**
 * T-122: цвет/толщина/прозрачность для карты маршрутов.
 *
 * Единый источник цветов — `lib/loadTier.COLORS` (тот же, что у карточек и
 * легенды, clinerule 31). Никакой второй палитры: «карта подсвечена как
 * карточки» = буквально те же hex'ы.
 *
 * Файл чистый (без React) — поэтому тестируется в jsdom без рендера карты.
 */

import type { MapColorScale } from '@/lib/geoRoutes';
import { COLORS } from '@/lib/loadTier';

/** Высота карты по умолчанию (px) — одинаковая у обоих провайдеров. */
export const MAP_VIEW_HEIGHT = 380;

/** Классический центр Москвы (fallback когда геоданных нет). */
export const MOSCOW_CENTER: [number, number] = [55.751244, 37.618423];

export const DEFAULT_ZOOM = 10;
export const SELECTED_ZOOM = 12;

export const SELECTED_OPACITY = 1;
export const UNSELECTED_OPACITY = 0.25;

export const MIN_LINE_WEIGHT = 2;
export const MAX_LINE_WEIGHT = 10;
export const MIN_STOP_RADIUS = 3;
export const MAX_STOP_RADIUS = 8;

function clamp(value: number, lo: number, hi: number): number {
  if (!Number.isFinite(value)) return lo;
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

/**
 * Hex линии/точки по tier'у. `unknown` (нет данных) и undefined → серый.
 * Значения — `border` из COLORS (насыщенный цвет, читаемый на карте).
 */
export function mapColorForTier(tier: MapColorScale | undefined | null): string {
  if (!tier || tier === 'unknown') return COLORS.gray.border;
  return COLORS[tier].border;
}

/** tier маршрута из индекса (undefined → 'unknown'). */
export function tierForRoute(
  tierByRoute: Readonly<Record<number, MapColorScale>> | undefined,
  routeId: number,
): MapColorScale {
  return tierByRoute?.[routeId] ?? 'unknown';
}

/**
 * Толщина линии ∝ загрузке (ТЗ §3.1.4: «толщина, зависящая от загрузки»).
 * Без данных — минимальная толщина.
 */
export function polylineWeight(loadPct: number | null | undefined): number {
  if (typeof loadPct !== 'number' || !Number.isFinite(loadPct)) return MIN_LINE_WEIGHT;
  return clamp(MIN_LINE_WEIGHT + loadPct / 25, MIN_LINE_WEIGHT, MAX_LINE_WEIGHT);
}

/** Радиус точки остановки ∝ загрузке маршрута. */
export function stopRadius(loadPct: number | null | undefined): number {
  if (typeof loadPct !== 'number' || !Number.isFinite(loadPct)) return MIN_STOP_RADIUS;
  return clamp(MIN_STOP_RADIUS + loadPct / 50, MIN_STOP_RADIUS, MAX_STOP_RADIUS);
}

/**
 * Прозрачность маршрута: выбранный (или когда ничего не выбрано) — 1.0,
 * остальные при выборе — 0.25 (визуальный фокус без скрытия контекста).
 */
export function routeOpacity(isSelected: boolean, hasSelection: boolean): number {
  if (!hasSelection) return SELECTED_OPACITY;
  return isSelected ? SELECTED_OPACITY : UNSELECTED_OPACITY;
}
