/**
 * T-200 (новая редакция): HorizonToggle — 3 кнопки-плашки для горизонта.
 *
 * По запросу пользователя 2026-09-27:
 *  - убрать горизонт 30 минут
 *  - дефолт = 1 день
 *  - добавить 3 месяца и 1 год
 *
 * Что меняется в API:
 *  GET /api/v1/insights/alerts?window_min=N
 *  N ∈ {1440 (1 день), 131400 (3 мес), 525600 (1 год)}
 */

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { HorizonToggle, type HorizonKey } from './HorizonToggle';

const DEFAULT_KEY: HorizonKey = '1d';

describe('<HorizonToggle>', () => {
  it('renders three buttons: 1 день, 3 месяца, 1 год', () => {
    render(<HorizonToggle value={DEFAULT_KEY} onChange={() => undefined} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(3);
    expect(buttons[0]?.textContent).toMatch(/1 день/i);
    expect(buttons[1]?.textContent).toMatch(/3 месяца/i);
    expect(buttons[2]?.textContent).toMatch(/1 год/i);
  });

  it('marks the selected horizon with aria-pressed=true', () => {
    render(<HorizonToggle value="3m" onChange={() => undefined} />);
    expect(screen.getByRole('button', { name: /3 месяца/i }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: /1 день/i }).getAttribute('aria-pressed')).toBe('false');
  });

  it('emits the new key when a different button is clicked', () => {
    const onChange = vi.fn();
    render(<HorizonToggle value="1d" onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /1 год/i }));
    expect(onChange).toHaveBeenCalledWith('1y');
  });

  it('does not re-emit when the already-selected button is clicked', () => {
    const onChange = vi.fn();
    render(<HorizonToggle value="3m" onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /3 месяца/i }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
