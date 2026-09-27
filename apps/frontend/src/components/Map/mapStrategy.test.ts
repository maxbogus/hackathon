/**
 * T-122 / D-003: выбор провайдера карты.
 *
 * Ключевое свойство безопасности демо: Яндекс включается ТОЛЬКО при
 * (`VITE_MAP_IMPL=yandex`) И (реальный ключ). Всё остальное → OSM (Leaflet),
 * который работает без ключей.
 */

import { describe, expect, it } from 'vitest';

import { selectMapImpl } from './mapStrategy';

describe('selectMapImpl', () => {
  it('returns osm by default (no env, no key)', () => {
    expect(selectMapImpl(undefined, false)).toBe('osm');
    expect(selectMapImpl(undefined, true)).toBe('osm');
  });

  it('returns osm when yandex is requested but there is no key', () => {
    expect(selectMapImpl('yandex', false)).toBe('osm');
  });

  it('returns yandex only when requested AND the key exists', () => {
    expect(selectMapImpl('yandex', true)).toBe('yandex');
  });

  it('ignores unknown values', () => {
    expect(selectMapImpl('2gis', true)).toBe('osm');
    expect(selectMapImpl('', true)).toBe('osm');
    expect(selectMapImpl(null, true)).toBe('osm');
  });
});
