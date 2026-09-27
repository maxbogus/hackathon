/**
 * T-218: <PassengerMode> показывает ДВА блока (clinerule 31):
 *  - actuals (как было)
 *  - predictions (как будет)
 *
 * Источники:
 *  - GET /api/v1/historical/load  → avg boardings per route (actuals)
 *  - GET /api/v1/predictions/load → avg boardings per route (predictions)
 *  - GET /api/v1/models/active   → активная модель для footer
 *
 * T-218+: карточка actual теперь показывает:
 *   - фактическое число пассажиров (boardings)
 *   - прогноз на этот же routeId
 *   - отклонение actual vs prediction, в %
 * Цвет по асимметричной шкале (over=hot, under=cool, normal=green, unknown=gray).
 */

import { describe, expect, it, vi, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { PassengerMode } from './PassengerMode';

/**
 * T-122: карта мокается — Leaflet/Yandex не рендерятся в jsdom
 * (см. components/Map/README.md). Проверяем проводку: геометрия из
 * /geo/routes доехала до карты, а выбор синхронизирован с карточками.
 */
vi.mock('@/components/Map/MapProvider', () => ({
  RouteMap: ({
    routes,
    selectedRouteId,
  }: {
    routes: readonly { routeId: number }[];
    selectedRouteId?: number | null;
  }) => (
    <div
      data-testid="route-map-stub"
      data-routes={routes.length}
      data-selected={selectedRouteId === null || selectedRouteId === undefined ? '' : String(selectedRouteId)}
    />
  ),
}));

const ROUTES = [1, 7, 11, 12, 17, 25, 26, 28, 50];
const ACTIVE_MODEL_PAYLOAD = {
  model_id: 'baseline_v1',
  metrics: { wape_score: 0.9272, rmsle: 0.23 },
};

afterEach(() => {
  vi.restoreAllMocks();
});

function mockLoadApi(opts: {
  actualsByRoute?: Record<number, number>;
  predictionsByRoute?: Record<number, number>;
  modelPayload?: object | null;
  actualsEmpty?: boolean;
  predictionsEmpty?: boolean;
  geoEmpty?: boolean;
} = {}): void {
  const actualsByRoute = opts.actualsByRoute ?? {};
  const predictionsByRoute = opts.predictionsByRoute ?? {};
  const modelPayload = opts.modelPayload ?? ACTIVE_MODEL_PAYLOAD;
  const actualsEmpty = !!opts.actualsEmpty;
  const predictionsEmpty = !!opts.predictionsEmpty;
  const geoEmpty = !!opts.geoEmpty;

  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();

    if (url.includes('/api/v1/historical/load')) {
      const loads = actualsEmpty
        ? []
        : ROUTES.map((rid) => {
            const v = actualsByRoute[rid] ?? 60;
            return {
              route_id: rid,
              boardings_avg: v,
              load_pct: (v / 150) * 100,
              tier: (v / 150) * 100 < 70 ? 'green' : (v / 150) * 100 < 90 ? 'yellow' : (v / 150) * 100 < 110 ? 'red' : 'darkred',
              sample_size: 24,
              period_start: '2025-10-30T00:00:00Z',
              period_end: '2025-10-30T23:00:00Z',
            };
          });
      return new Response(
        JSON.stringify({
          loads,
          count: loads.length,
          source: 'actuals',
          used_fallback: true,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      );
    }

    if (url.includes('/api/v1/predictions/load')) {
      const loads = predictionsEmpty
        ? []
        : ROUTES.map((rid) => {
            const v = predictionsByRoute[rid] ?? 60;
            return {
              route_id: rid,
              boardings_avg: v,
              load_pct: (v / 150) * 100,
              tier: (v / 150) * 100 < 70 ? 'green' : (v / 150) * 100 < 90 ? 'yellow' : (v / 150) * 100 < 110 ? 'red' : 'darkred',
              sample_size: 24,
            };
          });
      return new Response(
        JSON.stringify({
          loads,
          count: loads.length,
          source: 'predictions',
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      );
    }

    if (url.includes('/api/v1/geo/routes')) {
      const routes = geoEmpty
        ? []
        : ROUTES.map((rid) => ({
            route_id: rid,
            n_stops: 2,
            stops: [
              { name: `Остановка ${rid}-1`, lat: 55.8, lon: 37.7, order: 0 },
              { name: `Остановка ${rid}-2`, lat: 55.81, lon: 37.71, order: 1 },
            ],
          }));
      return new Response(
        JSON.stringify({
          routes,
          count: routes.length,
          source: 'external/stops_routes.json',
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

describe('<PassengerMode> — два блока actuals+predictions', () => {
  it('does NOT render a stop selector', async () => {
    mockLoadApi();
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.queryByRole('combobox')).toBeNull();
    });
  });

  it('renders both grids: actuals-grid and predictions-grid', async () => {
    mockLoadApi();
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByTestId('actuals-grid')).toBeInTheDocument();
      expect(screen.getByTestId('predictions-grid')).toBeInTheDocument();
    });
  });

  it('renders N route load cards per grid (one per route)', async () => {
    mockLoadApi();
    render(<PassengerMode />);
    await waitFor(() => {
      const actualsCards = screen.getByTestId('actuals-grid').querySelectorAll('[data-testid="route-load-card"]');
      const predictionsCards = screen.getByTestId('predictions-grid').querySelectorAll('[data-testid="route-load-card"]');
      expect(actualsCards.length).toBe(ROUTES.length);
      expect(predictionsCards.length).toBe(ROUTES.length);
    });
  });

  it('renders legend with 6 color tiers', async () => {
    mockLoadApi();
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByTestId('load-legend')).toBeInTheDocument();
      expect(screen.getByTestId('legend-green')).toBeInTheDocument();
      expect(screen.getByTestId('legend-lightblue')).toBeInTheDocument();
      expect(screen.getByTestId('legend-darkred')).toBeInTheDocument();
    });
  });

  it('shows actuals card with passenger count + deviation when actual > prediction', async () => {
    // actual=120, prediction=100 → +20% → tier=yellow, side=over
    mockLoadApi({ actualsByRoute: { 7: 120 }, predictionsByRoute: { 7: 100 } });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('actuals-grid', 7);
      expect(card).toBeDefined();
      expect(card?.textContent).toMatch(/120 чел/);
      expect(card?.textContent).toMatch(/\+20\.0%/);
      expect(card?.getAttribute('data-side')).toBe('over');
      expect(card?.getAttribute('data-tier')).toBe('yellow');
    });
  });

  it('shows actuals card in lightblue when actual < prediction (under)', async () => {
    // actual=30, prediction=100 → -70% → side=under → рендерится lightblue
    mockLoadApi({ actualsByRoute: { 17: 30 }, predictionsByRoute: { 17: 100 } });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('actuals-grid', 17);
      expect(card?.getAttribute('data-side')).toBe('under');
      expect(card?.textContent).toMatch(/30 чел/);
      expect(card?.textContent).toMatch(/-70\.0%/);
    });
  });

  it('shows actuals card in green when |dev| < 15%', async () => {
    // actual=105, prediction=100 → +5% → side=normal, tier=green
    mockLoadApi({ actualsByRoute: { 25: 105 }, predictionsByRoute: { 25: 100 } });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('actuals-grid', 25);
      expect(card?.getAttribute('data-side')).toBe('normal');
      expect(card?.getAttribute('data-tier')).toBe('green');
    });
  });

  it('shows actuals card in darkred when actual >> prediction', async () => {
    // actual=200, prediction=100 → +100% → side=over, tier=darkred
    mockLoadApi({ actualsByRoute: { 11: 200 }, predictionsByRoute: { 11: 100 } });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('actuals-grid', 11);
      expect(card?.getAttribute('data-tier')).toBe('darkred');
      expect(card?.textContent).toMatch(/\+100\.0%/);
    });
  });

  it('actuals card with missing prediction → side=unknown (gray)', async () => {
    // Если actual route_id отсутствует в predictions → actual-карточка покажет gray
    mockLoadApi({ actualsByRoute: { 7: 80 }, predictionsEmpty: true });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('actuals-grid', 7);
      expect(card?.getAttribute('data-side')).toBe('unknown');
      expect(card?.textContent).toMatch(/80 чел/);
    });
  });

  it('prediction card does NOT show "нет прогноза" under the forecast number', async () => {
    // Regression (F-097): prediction-карточка всегда получала boardings из predictions,
    // но predictionBoardings не передавалось → computeDeviation(null) → подпись
    // «нет прогноза» под САМИМ числом прогноза.
    mockLoadApi({ predictionsByRoute: { 7: 100 } });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('predictions-grid', 7);
      expect(card).toBeDefined();
      expect(card?.textContent).toMatch(/100 чел/);
      // Под числом прогноза не должно быть «нет прогноза» и не должно быть +/-0.0%.
      expect(card?.textContent).not.toMatch(/нет прогноза/);
      expect(card?.textContent).not.toMatch(/[+-]0\.0%/);
    });
  });

  it('actuals card without matching prediction shows "нет прогноза" (existing behavior)', async () => {
    // Контр-тест: actual-карточка БЕЗ прогноза по тому же routeId должна
    // показывать «нет прогноза» (as designed in T-218+).
    mockLoadApi({ actualsByRoute: { 7: 80 }, predictionsEmpty: true });
    render(<PassengerMode />);
    await waitFor(() => {
      const card = cardByRoute('actuals-grid', 7);
      expect(card).toBeDefined();
      expect(card?.textContent).toMatch(/80 чел/);
      expect(card?.textContent).toMatch(/нет прогноза/);
    });
  });

  it('keeps showing cards when /models/active is down', async () => {
    mockLoadApi({ modelPayload: null });
    render(<PassengerMode />);
    await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      expect(cards.length).toBe(ROUTES.length * 2); // both grids
    });
  });

  it('shows "как было" and "как будет" headers (i18n)', async () => {
    mockLoadApi();
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByText(/как было/i)).toBeInTheDocument();
      expect(screen.getByText(/как будет/i)).toBeInTheDocument();
    });
  });
});

/**
 * T-122: карта маршрутов + синхронизация с карточками.
 *
 * Провайдер мокается (jsdom не рендерит Leaflet/Yandex) — проверяем контракт:
 * геометрия из /geo/routes доехала, выбор ходит в обе стороны.
 */
describe('<PassengerMode> — карта маршрутов (T-122)', () => {
  it('passes the route geometry from /geo/routes to the map', async () => {
    mockLoadApi();
    render(<PassengerMode />);

    await waitFor(() => {
      expect(screen.getByTestId('route-map-stub')).toHaveAttribute(
        'data-routes',
        String(ROUTES.length),
      );
    });
  });

  it('keeps rendering the map section when geometry is unavailable', async () => {
    mockLoadApi({ geoEmpty: true });
    render(<PassengerMode />);

    await waitFor(() => {
      expect(screen.getByTestId('route-map-stub')).toHaveAttribute('data-routes', '0');
    });
  });

  it('clicking a prediction card selects that route on the map', async () => {
    mockLoadApi({ predictionsByRoute: { 7: 90 } });
    render(<PassengerMode />);

    await waitFor(() => expect(screen.getByTestId('route-map-stub')).toBeInTheDocument());

    const card = cardByRoute('predictions-grid', 7);
    expect(card).toBeDefined();
    fireEvent.click(card as HTMLElement);

    await waitFor(() => {
      expect(screen.getByTestId('route-map-stub')).toHaveAttribute('data-selected', '7');
      expect(cardByRoute('predictions-grid', 7)?.getAttribute('data-selected')).toBe('true');
      expect(cardByRoute('predictions-grid', 1)?.getAttribute('data-selected')).toBe('false');
    });
  });

  it('clicking the same card twice clears the selection (toggle)', async () => {
    mockLoadApi();
    render(<PassengerMode />);

    await waitFor(() => expect(screen.getByTestId('route-map-stub')).toBeInTheDocument());

    const card = cardByRoute('actuals-grid', 11) as HTMLElement;
    fireEvent.click(card);
    await waitFor(() =>
      expect(screen.getByTestId('route-map-stub')).toHaveAttribute('data-selected', '11'),
    );

    fireEvent.click(card);
    await waitFor(() =>
      expect(screen.getByTestId('route-map-stub')).toHaveAttribute('data-selected', ''),
    );
  });

  it('selection is shared between both grids (same routeId)', async () => {
    mockLoadApi();
    render(<PassengerMode />);

    await waitFor(() => expect(screen.getByTestId('route-map-stub')).toBeInTheDocument());

    fireEvent.click(cardByRoute('actuals-grid', 25) as HTMLElement);

    await waitFor(() => {
      expect(cardByRoute('actuals-grid', 25)?.getAttribute('data-selected')).toBe('true');
      expect(cardByRoute('predictions-grid', 25)?.getAttribute('data-selected')).toBe('true');
    });
  });
});

/** Хелпер: найти карточку по grid + routeId. */
function cardByRoute(testId: string, routeId: number): HTMLElement | undefined {
  const grid = screen.getByTestId(testId);
  const cards = grid.querySelectorAll<HTMLElement>('[data-testid="route-load-card"]');
  return Array.from(cards).find((c) => c.getAttribute('data-route-id') === String(routeId));
}
