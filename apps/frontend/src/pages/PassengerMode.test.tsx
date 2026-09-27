/**
 * T-200 (новая редакция): <PassengerMode> показывает нагрузку по всем
 * доступным маршрутам (10 трамвайных линий Москвы). Никаких остановок —
 * только сетка карточек с номером маршрута и текущей загрузкой.
 *
 * Что на экране:
 *  - заголовок «Нагрузка по линиям»
 *  - сетка <RouteLoadCard> × 10 (по одной на маршрут)
 *  - каждая карточка раскрашена по 4-уровневой шкале (loadTier)
 *  - подвал: «Модель: baseline_v1 · WAPE-score 0.9272»
 *
 * Источник данных:
 *  - список маршрутов: GET /api/v1/historical → routes[]
 *  - нагрузка: GET /api/v1/historical/{route_id}?granularity=hour (последний час)
 *  - активная модель: GET /api/v1/models/active
 */

import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

import { PassengerMode } from './PassengerMode';

const ROUTES = [1, 7, 11, 12, 17, 25, 26, 28, 50];
const ACTIVE_MODEL_PAYLOAD = {
  model_id: 'baseline_v1',
  metrics: { wape_score: 0.9272, rmsle: 0.23 },
};

afterEach(() => {
  vi.restoreAllMocks();
});

function mockApi(opts: {
  routes?: number[];
  perRouteValue?: Record<number, number>;
  modelPayload?: object | null;
} = {}): void {
  const routes = opts.routes ?? ROUTES;
  const perRouteValue = opts.perRouteValue ?? {};
  const modelPayload = opts.modelPayload ?? ACTIVE_MODEL_PAYLOAD;

  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();

    if (url.includes('/api/v1/historical') && !url.match(/\/historical\/\d/)) {
      // /api/v1/historical → list of routes
      return new Response(JSON.stringify({ routes, count: routes.length }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }

    const routeMatch = url.match(/\/api\/v1\/historical\/(\d+)/);
    if (routeMatch) {
      const routeId = Number(routeMatch[1]);
      // Default: 60 boardings/hour → 60/150 = 40% load (green)
      const value = perRouteValue[routeId] ?? 60;
      return new Response(
        JSON.stringify({
          route_id: routeId,
          granularity: 'hour',
          points: [
            { period_start: '2025-09-30T20:00:00Z', period_end: '2025-09-30T21:00:00Z', value },
          ],
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      );
    }

    if (url.includes('/api/v1/models/active')) {
      if (modelPayload === null) {
        return new Response('boom', { status: 503 });
      }
      return new Response(JSON.stringify(modelPayload), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }

    return new Response('not found', { status: 404 });
  }) as typeof global.fetch;
}

describe('<PassengerMode> — нагрузка по линиям', () => {
  it('does NOT render a stop selector (T-200: убрали остановки)', async () => {
    mockApi();
    render(<PassengerMode />);
    await waitFor(() => {
      // Никаких <select> с остановками
      expect(screen.queryByRole('combobox')).toBeNull();
    });
  });

  it('renders one <RouteLoadCard> per route from /api/v1/historical', async () => {
    mockApi();
    render(<PassengerMode />);
    await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      expect(cards.length).toBe(ROUTES.length);
    });
  });

  it('each route card shows the route number and load percentage', async () => {
    mockApi({ perRouteValue: { 7: 120 } }); // 120/150 = 80% → yellow (70-90)
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByText('Маршрут 7')).toBeInTheDocument();
      // 120/150 = 80%
      expect(screen.getByText('80%')).toBeInTheDocument();
    });
  });

  it('colors the card yellow for load 80% (between 70 and 90)', async () => {
    mockApi({ perRouteValue: { 7: 120 } }); // 80%
    render(<PassengerMode />);
    const card = await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      const c = cards.find((el) => el.textContent?.includes('Маршрут 7'));
      if (!c) throw new Error('Маршрут 7 card not found');
      return c;
    });
    expect(card.getAttribute('data-tier')).toBe('yellow');
  });

  it('colors the card red for load 100% (between 90 and 110)', async () => {
    mockApi({ perRouteValue: { 1: 150 } }); // 100%
    render(<PassengerMode />);
    const card = await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      const c = cards.find((el) => el.textContent?.includes('Маршрут 1'));
      if (!c) throw new Error('Маршрут 1 card not found');
      return c;
    });
    expect(card.getAttribute('data-tier')).toBe('red');
  });

  it('colors the card green for low load (60/150 = 40%)', async () => {
    mockApi({ perRouteValue: { 11: 60 } }); // 40%
    render(<PassengerMode />);
    const card = await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      const c = cards.find((el) => el.textContent?.includes('Маршрут 11'));
      if (!c) throw new Error('Маршрут 11 card not found');
      return c;
    });
    expect(card.getAttribute('data-tier')).toBe('green');
  });

  it('shows the active model + WAPE-score in the footer', async () => {
    mockApi();
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByText(/baseline_v1/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/0\.9272/i)).toBeInTheDocument();
  });

  it('keeps showing cards when /models/active is down (silent failure)', async () => {
    mockApi({ modelPayload: null });
    render(<PassengerMode />);
    await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      expect(cards.length).toBe(ROUTES.length);
    });
  });
});
