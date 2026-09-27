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
 * Covers AC-1 (role-switcher with three entries) at a minimal level. The
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
  it('renders a role-switcher with three role links (no planner — T-200)', async () => {
    renderWithProviders(<App />);
    expect(await screen.findByRole('link', { name: /пассажир/i })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /диспетчер/i })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /аналитик/i })).toBeInTheDocument();
    // T-200 / D-027: planner tab was removed.
    expect(screen.queryByRole('link', { name: /планировщик/i })).not.toBeInTheDocument();
  });

  it('redirects "/" to /passenger and renders the passenger panel', async () => {
    renderWithProviders(<App />);
    expect(
      await screen.findByRole('heading', { name: /пассажир.*нагрузка по линиям/i }),
    ).toBeInTheDocument();
  });
});
