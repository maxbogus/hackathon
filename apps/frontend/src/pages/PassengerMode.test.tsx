/**
 * T-129: RED phase — integration tests for the <PassengerMode> page.
 *
 * The page renders:
 *  - a <select> with all stops (loaded via getStops)
 *  - three <EtaCard>s with the closest trams (loaded via getEta)
 *  - a recommendation banner driven by recommend() (T-130)
 *
 * We mock `etaClient` so the tests stay synchronous-ish and don't need MSW.
 */

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { PassengerMode } from './PassengerMode';

// Mock the data layer. Real-mode behaviour is covered separately by
// etaClient.test.ts — here we only need to drive the page through React.
vi.mock('@/lib/etaClient', () => {
  return {
    getStops: vi.fn(async () => [
      { id: 1, name: 'Белорусская', lat: 55.7765, lon: 37.5842, routes: [7, 9] },
      { id: 2, name: 'Чистые пруды', lat: 55.7588, lon: 37.6387, routes: [3, 39] },
    ]),
    getEta: vi.fn(async (stopId: number) => {
      if (stopId === 1) {
        return [
          { route_id: 7, route_name: '7', eta_min: 2, predicted_load_pct: 35, model_id: 'm' },
          { route_id: 9, route_name: '9', eta_min: 6, predicted_load_pct: 78, model_id: 'm' },
          { route_id: 10, route_name: 'А', eta_min: 11, predicted_load_pct: 40, model_id: 'm' },
        ];
      }
      if (stopId === 2) {
        return [
          { route_id: 3, route_name: '3', eta_min: 1, predicted_load_pct: 95, model_id: 'm' },
          { route_id: 39, route_name: '39', eta_min: 6, predicted_load_pct: 60, model_id: 'm' },
        ];
      }
      return [];
    }),
  };
});

describe('<PassengerMode>', () => {
  it('renders a stop selector populated with all stops from the data layer', async () => {
    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /белорусская/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /чистые пруды/i })).toBeInTheDocument();
    });
  });

  it('renders exactly three <EtaCard>s for the initially selected stop', async () => {
    render(<PassengerMode />);
    // The first stop (id=1) has 3 trams in the mock; cards appear once data loads.
    // EtaCard sets data-testid="eta-card" on its root element so we count by that.
    await waitFor(() => {
      const cards = screen.getAllByTestId('eta-card');
      expect(cards.length).toBe(3);
    });
  });

  it('shows a recommendation banner driven by recommend()', async () => {
    render(<PassengerMode />);
    await waitFor(() => {
      // For the default mock stop (id=1, load 35%) recommend() returns
      // "Садитесь — будет комфортно" with success severity.
      expect(screen.getByText(/садитесь/i)).toBeInTheDocument();
    });
  });

  it('refetches ETA predictions when a different stop is selected', async () => {
    const { getEta } = await import('@/lib/etaClient');
    render(<PassengerMode />);
    await waitFor(() => screen.getByRole('combobox'));
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: '2' } });

    await waitFor(() => {
      expect(getEta).toHaveBeenCalledWith(2);
    });
  });

  it('handles the "no data" case gracefully when getEta returns []', async () => {
    const { getEta } = await import('@/lib/etaClient');
    (getEta as ReturnType<typeof vi.fn>).mockResolvedValueOnce([]);

    render(<PassengerMode />);
    await waitFor(() => {
      expect(screen.getByText(/нет данных/i)).toBeInTheDocument();
    });
  });

  it('shows the active model id from /api/v1/models/active in the footer (T-201)', async () => {
    // Mock fetch for /models/active (T-201: replace hard-coded "—" with
    // the active model id + WAPE-score fetched on mount).
    const originalFetch = global.fetch;
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.includes('/api/v1/models/active')) {
        return new Response(
          JSON.stringify({ model_id: 'baseline_v1', wape_score: 0.9272 }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }
      return originalFetch(input);
    }) as typeof global.fetch;

    try {
      render(<PassengerMode />);
      await waitFor(() => {
        expect(screen.getByText(/baseline_v1/i)).toBeInTheDocument();
      });
      // Footer should mention WAPE-score when available.
      expect(screen.getByText(/0\.9272|0\.93/i)).toBeInTheDocument();
    } finally {
      global.fetch = originalFetch;
    }
  });
});
