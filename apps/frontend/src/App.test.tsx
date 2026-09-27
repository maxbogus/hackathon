/**
 * T-129: smoke test for the role-switcher in App.tsx.
 *
 * T-135 / T-200: the role-switcher moved to URL-based routing. The three
 * remaining role entries are now <Link>s (role="link") rendered by the
 * root layout, and <App> mounts a <RouterProvider>. We assert the router
 * renders the passenger panel by default at "/".
 *
 * T-200 / D-027: planner was removed — three roles remain.
 *
 * T-225 / D-037: /passenger переименован в «Диспетчер» (UX-rename). Старая
 * вкладка /dispatcher (AlertsPanel) убрана из nav как orphan-роут.
 * T-222 follow-up: добавлена 3-я вкладка «📋 Прогноз · таблица» (PredictionsTable).
 * В nav остаются 3 ссылки: 🎛️ Диспетчер, 📊 Аналитик, 📋 Прогноз · таблица.
 *
 * Covers AC-1 (role-switcher with two entries) at a minimal level. The
 * deeper <PassengerMode> behaviour is covered by PassengerMode.test.tsx;
 * per-route outlet behaviour is covered by __root.test.tsx.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { App } from './App';

function renderWithProviders(ui: React.ReactElement): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        // Avoid real network in tests.
        retry: false,
        gcTime: 0,
      },
    },
  });
  render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('<App>', () => {
  it('renders a role-switcher with three role links (Диспетчер / Аналитик / Прогноз · таблица — T-225 + T-222)', async () => {
    renderWithProviders(<App />);
    // T-225: /passenger теперь называется «Диспетчер», /dispatcher удалён из nav.
    expect(await screen.findByRole('link', { name: /диспетчер/i })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /аналитик/i })).toBeInTheDocument();
    // T-222 follow-up: новая вкладка /predictions с TanStack Table v8.
    expect(await screen.findByRole('link', { name: /прогноз.*таблица/i })).toBeInTheDocument();
    // T-225: «Пассажир» в nav больше нет (был переименован).
    expect(screen.queryByRole('link', { name: /^🧍\s*пассажир$/i })).not.toBeInTheDocument();
    // T-200 / D-027: planner tab was removed.
    expect(screen.queryByRole('link', { name: /планировщик/i })).not.toBeInTheDocument();
    // Sanity: должно быть ровно 3 ссылки в nav.
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(3);
  });

  it('redirects "/" to /passenger and renders the passenger panel', async () => {
    renderWithProviders(<App />);
    expect(
      await screen.findByRole('heading', { name: /пассажир.*нагрузка по линиям/i }),
    ).toBeInTheDocument();
  });
});
