/**
 * T-131: AlertCard renders the time-to-overload and the severity pill,
 * and forwards release clicks to the parent.
 */

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { AlertCard } from './AlertCard';
import type { OverloadAlert } from '@/generated/api.schemas';

const ALERT_TEMPLATE: OverloadAlert = {
  stop_id: 1,
  route_id: 7,
  route_name: '7',
  predicted_load_pct: 92.5,
  time_to_overload_min: 8,
  severity: 'warning',
};

describe('<AlertCard>', () => {
  it('renders route_name and the predicted load_pct with one decimal', () => {
    render(<AlertCard alert={ALERT_TEMPLATE} />);
    expect(screen.getByText(/Маршрут 7/)).toBeInTheDocument();
    expect(screen.getByText(/92\.5%/)).toBeInTheDocument();
    expect(screen.getByTestId('time-to-overload').textContent).toContain('8 мин');
  });

  it('uses a critical pill for critical severity and an info pill for info', () => {
    const { rerender } = render(<AlertCard alert={{ ...ALERT_TEMPLATE, severity: 'critical' }} />);
    expect(screen.getByTestId('severity-pill').textContent).toMatch(/КРИТИЧНО/);
    rerender(<AlertCard alert={{ ...ALERT_TEMPLATE, severity: 'info' }} />);
    expect(screen.getByTestId('severity-pill').textContent).toMatch(/Инфо/);
  });

  it('calls onRelease with the alert when the button is clicked', () => {
    const onRelease = vi.fn();
    render(<AlertCard alert={ALERT_TEMPLATE} onRelease={onRelease} />);
    fireEvent.click(screen.getByRole('button', { name: /выпустить вагон/i }));
    expect(onRelease).toHaveBeenCalledTimes(1);
    expect(onRelease).toHaveBeenCalledWith(ALERT_TEMPLATE);
  });
});
