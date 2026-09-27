/**
 * T-218: <PassengerMode> показывает ДВА блока (clinerule 31):
 *  - actuals (как было)
 *  - predictions (как будет)
 *
 * Источники:
 *  - GET /api/v1/historical/load  → avg boardings per route (actuals)
 *  - GET /api/v1/predictions/load → avg boardings per route (predictions)
 *  - GET /api/v1/models/active   → активная модель для footer
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

function mockLoadApi(opts: {
  actualsByRoute?: Record<number, number>;
  predictionsByRoute?: Record<number, number>;
  modelPayload?: object | null;
  actualsEmpty?: boolean;
  predictionsEmpty?: boolean;
} = {}): void {
  const actualsByRoute = opts.actualsByRoute ?? {};
  const predictionsByRoute = opts.predictionsByRoute ?? {};
  const modelPayload = opts.modelPayload ?? ACTIVE_MODEL_PAYLOAD;
  const actualsEmpty = !!opts.actualsEmpty;
  const predictionsEmpty = !!opts.predictionsEmpty;

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

  it('shows percentage for predictions block', async () => {
    mockLoadApi({ predictionsByRoute: { 7: 120 } }); // 80%
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByText('80%')).toBeInTheDocument();
    });
  });

  it('colors predictions card yellow for load 80%', async () => {
    mockLoadApi({ predictionsByRoute: { 7: 120 } });
    render(<PassengerMode />);
    await waitFor(() => {
      const cards = screen.getAllByTestId('route-load-card');
      const inPredictions = cards.filter((c) => c.parentElement?.getAttribute('data-testid') === 'predictions-grid');
      const c = inPredictions.find((el) => el.textContent?.includes('Маршрут 7'));
      expect(c?.getAttribute('data-tier')).toBe('yellow');
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
