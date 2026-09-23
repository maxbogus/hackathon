/**
 * T-129: RED phase — tests for the <EtaCard> tram-arrival card.
 *
 * Each upcoming tram is shown as a card with route name, ETA (in minutes) and
 * predicted load percentage. The colour of the top border indicates how
 * crowded the tram will be:
 *
 *   load < 70          → green   (comfortable)
 *   load 70..90        → yellow  (grey zone)
 *   load 90..110       → red     (crowded)
 *   load >= 110        → darkred (over capacity)
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { EtaCard } from './EtaCard';
import type { ETAPrediction } from './recommend';

function tram(partial: Partial<ETAPrediction>): ETAPrediction {
  return {
    route_id: 7,
    route_name: '7',
    eta_min: 2,
    predicted_load_pct: 50,
    model_id: 'baseline_v1',
    ...partial,
  };
}

describe('<EtaCard>', () => {
  it('renders the route name', () => {
    render(<EtaCard tram={tram({ route_name: 'А' })} />);
    expect(screen.getByText('А')).toBeInTheDocument();
  });

  it('renders the ETA in minutes', () => {
    render(<EtaCard tram={tram({ eta_min: 4 })} />);
    expect(screen.getByText(/4 мин/i)).toBeInTheDocument();
  });

  it('renders the predicted load percentage', () => {
    render(<EtaCard tram={tram({ predicted_load_pct: 65 })} />);
    expect(screen.getByText(/65%/)).toBeInTheDocument();
  });

  it('applies the "green" colour class when load is below 70%', () => {
    const { container } = render(<EtaCard tram={tram({ predicted_load_pct: 30 })} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/green/i);
  });

  it('applies the "yellow" colour class when load is 70–90%', () => {
    const { container } = render(<EtaCard tram={tram({ predicted_load_pct: 80 })} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/yellow/i);
  });

  it('applies the "red" colour class when load is 90–110%', () => {
    const { container } = render(<EtaCard tram={tram({ predicted_load_pct: 95 })} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/red/i);
  });

  it('applies the "darkred" colour class when load exceeds 110%', () => {
    const { container } = render(<EtaCard tram={tram({ predicted_load_pct: 115 })} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/darkred/i);
  });

  it('shows a "🚉" indicator for trams that have already departed (eta_min = 0)', () => {
    render(<EtaCard tram={tram({ eta_min: 0 })} />);
    // When eta is 0 we render "🚉 Ушёл" instead of a minute count.
    expect(screen.getByText(/ушёл/i)).toBeInTheDocument();
  });
});
