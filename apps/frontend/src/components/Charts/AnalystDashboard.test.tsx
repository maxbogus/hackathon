/**
 * T-233: <AnalystDashboard> — переключатель маршрута должен менять данные обоих
 * графиков (истории и прогноза).
 *
 * Это wiring-тест, а не тест графиков: recharts в jsdom не рендерится
 * осмысленно, поэтому оба чарта и GeneratePanel замоканы стабами, которые
 * печатают полученный `routeId` (`data-route`). Графики не перезагружают
 * данные сами — они включены в `queryKey` внутри чартов (T-196/T-203), так что
 * проверяем именно то, что дашборд доносит новый маршрут до каждого из них.
 *
 * Данные каталога маршрутов замоканы на уровне модуля: логика объединения
 * `/historical` ∪ `/predictions/load` покрыта в lib/routeCatalog.test.ts.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AnalystDashboard } from './AnalystDashboard';

const mocks = vi.hoisted(() => ({
  fetchRouteCatalog: vi.fn(),
  customInstance: vi.fn(),
}));

vi.mock('@/lib/routeCatalog', () => ({
  CANONICAL_ROUTES: [1, 5, 7, 11, 12, 17, 25, 26, 28, 50],
  fetchRouteCatalog: mocks.fetchRouteCatalog,
}));

vi.mock('@/api/customInstance', () => ({
  customInstance: mocks.customInstance,
}));

// Чарты и панель генерации — вне скоупа теста (см. шапку файла).
vi.mock('@/components/Charts/HistoricalChart', () => ({
  HistoricalChart: ({ routeId }: { routeId: number }) => (
    <div data-testid="historical-stub" data-route={String(routeId)} />
  ),
}));

vi.mock('@/components/Charts/PredictionsChart', () => ({
  PredictionsChart: ({ routeId }: { routeId: number }) => (
    <div data-testid="predictions-stub" data-route={String(routeId)} />
  ),
}));

vi.mock('@/components/Analyst/GeneratePanel', () => ({
  GeneratePanel: () => <div data-testid="generate-panel-stub" />,
}));

const FEATURES = {
  feature_toggles: [
    { name: 'use_lag', description: 'Lag features', enabled: true, is_default: true },
  ],
  zero_overrides: [
    { name: 'zero_route_5', description: 'Route 5 closed', enabled: false, params: {} },
  ],
};

/**
 * Опции только селекта маршрута: на экране есть ещё <HorizonGranularity>
 * с двумя <select>, у которых тоже role="option" (горизонт/детализация).
 */
function routeOptionValues(select: HTMLElement): (string | null)[] {
  return within(select)
    .getAllByRole('option')
    .map((o) => o.getAttribute('value'));
}

function renderDashboard(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AnalystDashboard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mocks.fetchRouteCatalog.mockReset();
  mocks.customInstance.mockReset();
  mocks.fetchRouteCatalog.mockResolvedValue([1, 7, 17, 25]);
  mocks.customInstance.mockResolvedValue(FEATURES);
});

describe('<AnalystDashboard> route selector', () => {
  it('renders the routes coming from the catalog, with route 7 selected by default', async () => {
    renderDashboard();

    const select = await screen.findByTestId('route-select');
    expect(select).toHaveValue('7');
    expect(mocks.fetchRouteCatalog).toHaveBeenCalled();

    // Каталог приезжает асинхронно — до его ответа показываются канонические 10.
    await waitFor(() => expect(routeOptionValues(select)).toEqual(['1', '7', '17', '25']));
  });

  it('switching the route updates both charts', async () => {
    renderDashboard();

    const select = await screen.findByTestId('route-select');
    expect(screen.getByTestId('historical-stub')).toHaveAttribute('data-route', '7');
    expect(screen.getByTestId('predictions-stub')).toHaveAttribute('data-route', '7');

    fireEvent.change(select, { target: { value: '17' } });

    expect(screen.getByTestId('route-select')).toHaveValue('17');
    expect(screen.getByTestId('historical-stub')).toHaveAttribute('data-route', '17');
    expect(screen.getByTestId('predictions-stub')).toHaveAttribute('data-route', '17');
  });

  it('keeps the current route selectable even when the catalog omits it', async () => {
    mocks.fetchRouteCatalog.mockResolvedValue([1, 17, 25]);
    renderDashboard();

    const select = await screen.findByTestId('route-select');
    expect(select).toHaveValue('7'); // браузер сбросил бы value без такой <option>
    await waitFor(() => expect(routeOptionValues(select)).toEqual(['1', '7', '17', '25']));
  });

  it('stays usable (route selector + note) when /api/v1/features fails', async () => {
    mocks.customInstance.mockRejectedValue(new Error('HTTP 500'));
    renderDashboard();

    expect(await screen.findByTestId('route-select')).toHaveValue('7');
    expect(await screen.findByTestId('filters-features-error')).toBeInTheDocument();
    expect(screen.getByTestId('predictions-stub')).toBeInTheDocument();
  });

  it('uses the canonical routes until the catalog resolves', () => {
    mocks.fetchRouteCatalog.mockReturnValue(new Promise(() => undefined));
    renderDashboard();

    const select = screen.getByTestId('route-select');
    expect(routeOptionValues(select)).toEqual([
      '1',
      '5',
      '7',
      '11',
      '12',
      '17',
      '25',
      '26',
      '28',
      '50',
    ]);
  });
});
