/**
 * T-233: <RouteSelect> — переключатель маршрута на экране «Аналитик».
 *
 * Компонент полностью controlled: состояние живёт в <AnalystDashboard>,
 * компонент только рисует опции и эмитит onChange. В API не ходит — список
 * маршрутов приходит сверху (lib/routeCatalog.ts).
 *
 * Тестируем ровно то, что видит аналитик: подпись «Маршрут», опции, текущее
 * значение и то, что наружу уходит число (а не строка из <select>).
 */

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { RouteSelect } from './RouteSelect';

const ROUTES = [1, 7, 17, 25] as const;

describe('<RouteSelect>', () => {
  it('renders one option per route and exposes the label for screen readers', () => {
    render(<RouteSelect routes={ROUTES} value={7} onChange={() => undefined} />);

    const select = screen.getByTestId('route-select');
    expect(select).toBeInTheDocument();
    // Подпись «Маршрут» — та же, что была в статичной строке «Маршрут: 7».
    expect(screen.getByLabelText(/маршрут/i)).toBe(select);

    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(ROUTES.length);
    expect(options.map((o) => o.getAttribute('value'))).toEqual(['1', '7', '17', '25']);
  });

  it('reflects the current route from props', () => {
    render(<RouteSelect routes={ROUTES} value={17} onChange={() => undefined} />);

    expect(screen.getByTestId('route-select')).toHaveValue('17');
  });

  it('emits a number (not a string) when the user picks another route', () => {
    const onChange = vi.fn();
    render(<RouteSelect routes={ROUTES} value={7} onChange={onChange} />);

    fireEvent.change(screen.getByTestId('route-select'), { target: { value: '25' } });

    expect(onChange).toHaveBeenCalledWith(25);
  });

  it('renders an empty option list when no routes are available', () => {
    render(<RouteSelect routes={[]} value={7} onChange={() => undefined} />);

    expect(screen.queryAllByRole('option')).toHaveLength(0);
  });
});
