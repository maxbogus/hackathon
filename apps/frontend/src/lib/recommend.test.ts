/**
 * T-130: RED phase — failing tests for the passenger-mode `recommend()` helper.
 *
 * The function should turn a list of upcoming trams (with ETA and predicted load)
 * into an action-oriented recommendation: «board now», «wait — the next one will
 * be lighter», or «it's going to be tight — but there's no better option».
 *
 * The implementation lives in `./recommend.ts` and must be a **pure function**
 * (no React, no DOM) so it is trivial to unit test. The passenger-mode UI
 * (T-129) will import it and render the result via an MUI-style <Alert>.
 *
 * Pure-function tests only — no @testing-library/react needed here.
 */

import { describe, expect, it } from 'vitest';

import { recommend, type ETAPrediction } from './recommend';

function tram(partial: Partial<ETAPrediction>): ETAPrediction {
  // Default-shape factory — every test sets just the fields it cares about,
  // and `route_id`/`route_name` are stable so failure messages are readable.
  return {
    route_id: 10,
    route_name: 'А',
    eta_min: 1,
    predicted_load_pct: 50,
    model_id: 'baseline_v1',
    ...partial,
  };
}

describe('recommend()', () => {
  it('returns "no data" message when the input list is empty', () => {
    // AC boundary: backend returned no predictions.
    const result = recommend([]);
    expect(result.severity).toBe('info');
    expect(result.text).toMatch(/нет данных/i);
    expect(result.emoji).toBe('❓');
  });

  it('recommends boarding when the closest tram is comfortably empty (<70%)', () => {
    // AC-2: load 30% → board, severity = success.
    const result = recommend([tram({ predicted_load_pct: 30, eta_min: 2 })]);
    expect(result.severity).toBe('success');
    expect(result.text.toLowerCase()).toContain('садитесь');
  });

  it('still recommends boarding at the lower 70% boundary', () => {
    // AC-2 boundary value 69% — should be on the "comfortable" side.
    const result = recommend([tram({ predicted_load_pct: 69, eta_min: 1 })]);
    expect(result.severity).toBe('success');
  });

  it('suggests waiting when load is 70–90% and the next tram is soon AND notably emptier', () => {
    // AC-3 happy path: 80% load, next at 7 min with 50% load (Δ=-30 ≥ -15).
    const result = recommend([
      tram({ eta_min: 1, predicted_load_pct: 80 }),
      tram({ eta_min: 7, predicted_load_pct: 50 }),
    ]);
    expect(result.severity).toBe('info');
    expect(result.emoji).toBe('⏳');
    expect(result.text).toMatch(/подождите\s*7\s*мин/i);
  });

  it('does NOT suggest waiting in the 70–90% band when the next tram is far', () => {
    // AC-3 negation: 80% load but next is in 12 min — wait cost too high.
    const result = recommend([
      tram({ eta_min: 1, predicted_load_pct: 80 }),
      tram({ eta_min: 12, predicted_load_pct: 40 }),
    ]);
    expect(result.severity).toBe('success');
    expect(result.emoji).toBe('✅');
  });

  it('warns and suggests waiting when load is >90% and the next tram comes within 10 min', () => {
    // AC-4 happy path: 95% load, next at 6 min.
    const result = recommend([
      tram({ eta_min: 1, predicted_load_pct: 95 }),
      tram({ eta_min: 6, predicted_load_pct: 60 }),
    ]);
    expect(result.severity).toBe('warning');
    expect(result.emoji).toBe('⚠️');
    expect(result.text).toMatch(/подождите\s*6\s*мин/i);
    expect(result.text.toLowerCase()).toContain('свободнее');
  });

  it('warns with "no better option" when load is >90% and the next tram is too far to wait', () => {
    // AC-4 negation: 95% load, next in 15 min — not worth waiting.
    const result = recommend([
      tram({ eta_min: 1, predicted_load_pct: 95 }),
      tram({ eta_min: 15, predicted_load_pct: 30 }),
    ]);
    expect(result.severity).toBe('warning');
    expect(result.emoji).toBe('⚠️');
    // Negative phrasing — there is no good alternative, but tram is still coming.
    expect(result.text.toLowerCase()).toMatch(/вариантов\s+нет|других\s+вариантов/);
  });

  it('falls back to the next tram when the closest one has already departed (eta_min = 0)', () => {
    // AC-5: nearest tram "left" — skip it and base the recommendation on the second one
    // (which is at 40% load → board, success).
    const result = recommend([
      tram({ eta_min: 0, predicted_load_pct: 92 }),
      tram({ eta_min: 3, predicted_load_pct: 40 }),
    ]);
    expect(result.severity).toBe('success');
    expect(result.text.toLowerCase()).toContain('садитесь');
  });
});
