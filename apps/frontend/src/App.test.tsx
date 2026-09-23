/**
 * T-129: smoke test for the role-switcher in App.tsx.
 *
 * Covers AC-1 (role-switcher with four buttons) at a minimal level. The
 * deeper <PassengerMode> behaviour is covered by PassengerMode.test.tsx.
 */

import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { App } from './App';

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        // Avoid real network in tests.
        retry: false,
        gcTime: 0,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('<App>', () => {
  it('renders a role-switcher with four role buttons', () => {
    renderWithProviders(<App />);
    expect(screen.getByRole('button', { name: /пассажир/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /диспетчер/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /аналитик/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /планировщик/i })).toBeInTheDocument();
  });

  it('defaults to the passenger role', () => {
    renderWithProviders(<App />);
    // The passenger-mode <h2> is rendered by default.
    expect(screen.getByRole('heading', { name: /пассажир/i })).toBeInTheDocument();
  });

  it('switches to dispatcher panel when the dispatcher button is clicked', () => {
    renderWithProviders(<App />);
    fireEvent.click(screen.getByRole('button', { name: /диспетчер/i }));
    // The dispatcher panel is async (TanStack Query kicks off a fetch),
    // so we wait for the heading OR the loading state to confirm the panel
    // mounted. Full data rendering requires MSW or a backend mock (T-131-1).
    const heading = screen.queryByRole('heading', { name: /диспетчер.*алерты/i });
    const loading = screen.queryByTestId('alerts-loading');
    expect(heading ?? loading).toBeTruthy();
  });
});
