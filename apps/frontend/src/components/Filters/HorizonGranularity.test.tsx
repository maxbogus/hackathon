/**
 * T-203: HorizonGranularity selector.
 *
 * Two <select>s — for horizon (day|month|year) and granularity
 * (hour|day|month). The component is fully controlled: parent owns the
 * state, child emits onChange.
 *
 * Defaults from /api/v1/predictions/db/{route_id} (T-195):
 *   horizon    = 'day'
 *   granularity = 'hour'
 *
 * The component does not call any backend — the chart does that. This
 * keeps the selector pure and easy to test.
 */

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { HorizonGranularity } from './HorizonGranularity';

describe('<HorizonGranularity>', () => {
  it('renders two selects with horizon=day, granularity=hour by default', () => {
    render(
      <HorizonGranularity horizon="day" granularity="hour" onChange={() => undefined} />,
    );
    expect(screen.getByLabelText(/горизонт/i)).toHaveValue('day');
    expect(screen.getByLabelText(/детализация/i)).toHaveValue('hour');
  });

  it('emits the new horizon when the user picks "month"', () => {
    const onChange = vi.fn();
    render(<HorizonGranularity horizon="day" granularity="hour" onChange={onChange} />);

    fireEvent.change(screen.getByLabelText(/горизонт/i), { target: { value: 'month' } });
    expect(onChange).toHaveBeenCalledWith({ horizon: 'month', granularity: 'hour' });
  });

  it('emits the new granularity when the user picks "day"', () => {
    const onChange = vi.fn();
    render(<HorizonGranularity horizon="day" granularity="hour" onChange={onChange} />);

    fireEvent.change(screen.getByLabelText(/детализация/i), { target: { value: 'day' } });
    expect(onChange).toHaveBeenCalledWith({ horizon: 'day', granularity: 'day' });
  });

  it('exposes all three horizon options and three granularity options', () => {
    render(
      <HorizonGranularity horizon="day" granularity="hour" onChange={() => undefined} />,
    );
    const horizon = screen.getByLabelText(/горизонт/i) as HTMLSelectElement;
    const granularity = screen.getByLabelText(/детализация/i) as HTMLSelectElement;
    expect(Array.from(horizon.options).map((o) => o.value)).toEqual(['day', 'month', 'year']);
    expect(Array.from(granularity.options).map((o) => o.value)).toEqual([
      'hour',
      'day',
      'month',
    ]);
  });
});
