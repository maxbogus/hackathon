/**
 * T-122: <RouteMap> — фабрика провайдеров карты.
 *
 * Ленивые реализации мокаются: Leaflet/Yandex требуют реального DOM/сети
 * (Leaflet рисует тайлы, Yandex грузит внешний скрипт), в jsdom это
 * не воспроизводится. Проверяем ровно то, что принадлежит фабрике:
 * выбор провайдера, fallback при отсутствии ключа, пустой каталог.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { RouteMap } from './MapProvider';
import type { MapRoute, RouteMapProps } from './types';

vi.mock('./LeafletMap', () => ({
  default: ({ routes }: RouteMapProps) => (
    <div data-testid="leaflet-map" data-routes={routes.length} />
  ),
}));

vi.mock('./YandexMap', () => ({
  default: ({ routes }: RouteMapProps) => (
    <div data-testid="yandex-map" data-routes={routes.length} />
  ),
}));

const REAL_KEY = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
const PLACEHOLDER_KEY = 'your_key_here';

const ROUTES: readonly MapRoute[] = [
  {
    routeId: 7,
    stops: [
      { name: 'Бульвар Рокоссовского', lat: 55.8145, lon: 37.7342, order: 0 },
      { name: 'Игральная', lat: 55.8112, lon: 37.7248, order: 1 },
    ],
  },
];

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe('<RouteMap> — выбор провайдера', () => {
  it('defaults to OSM/Leaflet when nothing is configured', async () => {
    // Явные пустые значения: Vite читает корневой .env (envDir), где у
    // разработчика может стоять yandex — тест не должен от этого зависеть.
    vi.stubEnv('VITE_MAP_IMPL', '');
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', '');

    render(<RouteMap routes={ROUTES} />);

    expect(screen.getByTestId('route-map')).toHaveAttribute('data-impl', 'osm');
    const leaflet = await screen.findByTestId('leaflet-map');
    expect(leaflet).toHaveAttribute('data-routes', '1');
    expect(screen.queryByTestId('yandex-map')).toBeNull();
  });

  it('stays on OSM and warns when yandex is requested without a key', async () => {
    vi.stubEnv('VITE_MAP_IMPL', 'yandex');
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', '');

    render(<RouteMap routes={ROUTES} />);

    expect(screen.getByTestId('route-map')).toHaveAttribute('data-impl', 'osm');
    expect(await screen.findByTestId('leaflet-map')).toBeInTheDocument();
    expect(screen.getByTestId('route-map-key-warning')).toBeInTheDocument();
  });

  it('treats the .env.example placeholder as "no key"', async () => {
    vi.stubEnv('VITE_MAP_IMPL', 'yandex');
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', PLACEHOLDER_KEY);

    render(<RouteMap routes={ROUTES} />);

    expect(screen.getByTestId('route-map')).toHaveAttribute('data-impl', 'osm');
    expect(screen.getByTestId('route-map-key-warning')).toBeInTheDocument();
  });

  it('switches to Yandex when requested AND a real key is present', async () => {
    vi.stubEnv('VITE_MAP_IMPL', 'yandex');
    vi.stubEnv('VITE_YANDEX_MAPS_API_KEY', REAL_KEY);

    render(<RouteMap routes={ROUTES} />);

    expect(screen.getByTestId('route-map')).toHaveAttribute('data-impl', 'yandex');
    expect(await screen.findByTestId('yandex-map')).toBeInTheDocument();
    expect(screen.queryByTestId('leaflet-map')).toBeNull();
    expect(screen.queryByTestId('route-map-key-warning')).toBeNull();
  });
});

describe('<RouteMap> — пустой каталог', () => {
  it('renders the empty notice and no provider at all', () => {
    render(<RouteMap routes={[]} />);

    expect(screen.getByTestId('route-map-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('leaflet-map')).toBeNull();
    expect(screen.queryByTestId('yandex-map')).toBeNull();
    expect(screen.queryByTestId('route-map-loading')).toBeNull();
  });
});

describe('<RouteMap> — подписи', () => {
  it('renders the i18n title and hint (no hardcoded copy)', () => {
    render(<RouteMap routes={ROUTES} />);

    expect(screen.getByText('🗺️ Карта маршрутов')).toBeInTheDocument();
    expect(screen.getByTestId('route-map')).toHaveAttribute(
      'aria-label',
      'Карта трамвайных маршрутов Москвы',
    );
  });
});
