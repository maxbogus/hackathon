/**
 * T-129: smoke test for the role-switcher in App.tsx.
 *
 * Covers AC-1 (role-switcher with four buttons) at a minimal level. The
 * deeper <PassengerMode> behaviour is covered by PassengerMode.test.tsx.
 */

import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { App } from './App';

describe('<App>', () => {
  it('renders a role-switcher with four role buttons', () => {
    render(<App />);
    expect(screen.getByRole('button', { name: /пассажир/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /диспетчер/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /аналитик/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /планировщик/i })).toBeInTheDocument();
  });

  it('defaults to the passenger role', () => {
    render(<App />);
    // The passenger-mode <h2> is rendered by default.
    expect(screen.getByRole('heading', { name: /пассажир/i })).toBeInTheDocument();
  });

  it('switches to dispatcher placeholder when the dispatcher button is clicked', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /диспетчер/i }));
    // The dispatcher placeholder shows a description referencing T-131.
    expect(screen.getByText(/T-131/)).toBeInTheDocument();
  });
});
