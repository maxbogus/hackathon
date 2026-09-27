/**
 * T-122: карта не имеет собственной палитры — цвета берутся из
 * `lib/loadTier.COLORS` (тот же источник, что у карточек и легенды).
 * Эти тесты фиксируют связь: если кто-то «поправит» hex на карте,
 * тест упадёт — карта перестанет совпадать с карточками.
 */

import { describe, expect, it } from 'vitest';

import { COLORS } from '@/lib/loadTier';

import {
  MAX_LINE_WEIGHT,
  MAX_STOP_RADIUS,
  MIN_LINE_WEIGHT,
  MIN_STOP_RADIUS,
  SELECTED_OPACITY,
  UNSELECTED_OPACITY,
  mapColorForTier,
  polylineWeight,
  routeOpacity,
  stopRadius,
  tierForRoute,
} from './mapColors';

describe('mapColorForTier', () => {
  it('uses exactly the loadTier.COLORS border colours (single source of truth)', () => {
    expect(mapColorForTier('green')).toBe(COLORS.green.border);
    expect(mapColorForTier('yellow')).toBe(COLORS.yellow.border);
    expect(mapColorForTier('red')).toBe(COLORS.red.border);
    expect(mapColorForTier('darkred')).toBe(COLORS.darkred.border);
  });

  it('falls back to the gray border for unknown / undefined / null', () => {
    expect(mapColorForTier('unknown')).toBe(COLORS.gray.border);
    expect(mapColorForTier(undefined)).toBe(COLORS.gray.border);
    expect(mapColorForTier(null)).toBe(COLORS.gray.border);
  });
});

describe('polylineWeight', () => {
  it('is minimal without data', () => {
    expect(polylineWeight(null)).toBe(MIN_LINE_WEIGHT);
    expect(polylineWeight(undefined)).toBe(MIN_LINE_WEIGHT);
    expect(polylineWeight(Number.NaN)).toBe(MIN_LINE_WEIGHT);
  });

  it('grows with load_pct', () => {
    expect(polylineWeight(100)).toBeGreaterThan(polylineWeight(0));
    expect(polylineWeight(200)).toBeGreaterThan(polylineWeight(100));
  });

  it('is clamped to [MIN, MAX]', () => {
    expect(polylineWeight(-1000)).toBe(MIN_LINE_WEIGHT);
    expect(polylineWeight(1e6)).toBe(MAX_LINE_WEIGHT);
  });
});

describe('stopRadius', () => {
  it('is clamped and grows with load_pct', () => {
    expect(stopRadius(null)).toBe(MIN_STOP_RADIUS);
    expect(stopRadius(-5)).toBe(MIN_STOP_RADIUS);
    expect(stopRadius(1e6)).toBe(MAX_STOP_RADIUS);
    expect(stopRadius(120)).toBeGreaterThan(stopRadius(20));
  });
});

describe('routeOpacity', () => {
  it('keeps everything opaque when nothing is selected', () => {
    expect(routeOpacity(false, false)).toBe(SELECTED_OPACITY);
    expect(routeOpacity(true, false)).toBe(SELECTED_OPACITY);
  });

  it('dims unselected routes when a selection exists', () => {
    expect(routeOpacity(true, true)).toBe(SELECTED_OPACITY);
    expect(routeOpacity(false, true)).toBe(UNSELECTED_OPACITY);
  });
});

describe('tierForRoute', () => {
  it('reads the tier index and defaults to unknown', () => {
    expect(tierForRoute({ 7: 'red' }, 7)).toBe('red');
    expect(tierForRoute({ 7: 'red' }, 1)).toBe('unknown');
    expect(tierForRoute(undefined, 7)).toBe('unknown');
  });
});
