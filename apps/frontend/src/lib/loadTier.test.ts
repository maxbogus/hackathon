/**
 * T-218+ — тесты на deviationInfo / computeDeviation / visualFor.
 * loadTier() покрывается косвенно (PassengerMode.test.tsx).
 *
 * Асимметричная шкала (отзыв пользователя):
 *   over  (actual > pred):  yellow → red → darkred
 *   under (actual < pred):  lightblue (один уровень)
 *   normal (|dev| < 15%):   green
 *   unknown:                gray
 */

import { describe, expect, it } from 'vitest';

import {
  COLORS,
  computeDeviation,
  deviationInfo,
  loadTier,
  visualFor,
} from './loadTier';

describe('loadTier (legacy, load_pct vs TRAM_CAPACITY)', () => {
  it('green/yellow/red/darkred by bucket', () => {
    expect(loadTier(0)).toBe('green');
    expect(loadTier(69.9)).toBe('green');
    expect(loadTier(70)).toBe('yellow');
    expect(loadTier(89.9)).toBe('yellow');
    expect(loadTier(90)).toBe('red');
    expect(loadTier(109.9)).toBe('red');
    expect(loadTier(110)).toBe('darkred');
    expect(loadTier(1780)).toBe('darkred');
  });
});

describe('computeDeviation', () => {
  it('positive when actual > prediction', () => {
    expect(computeDeviation(120, 100)).toBeCloseTo(20, 5);
  });

  it('negative when actual < prediction', () => {
    expect(computeDeviation(80, 100)).toBeCloseTo(-20, 5);
  });

  it('zero when equal', () => {
    expect(computeDeviation(100, 100)).toBe(0);
  });

  it('null when actual or prediction is null', () => {
    expect(computeDeviation(null, 100)).toBeNull();
    expect(computeDeviation(100, null)).toBeNull();
    expect(computeDeviation(null, null)).toBeNull();
  });

  it('null when prediction is zero', () => {
    expect(computeDeviation(50, 0)).toBeNull();
  });

  it('null when not finite', () => {
    expect(computeDeviation(Number.NaN, 100)).toBeNull();
    expect(computeDeviation(100, Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe('deviationInfo — асимметричная шкала', () => {
  describe('over (actual > prediction)', () => {
    it('yellow: +15..+30%', () => {
      expect(deviationInfo(15)).toEqual({ side: 'over', magnitudePct: 15, tier: 'yellow' });
      expect(deviationInfo(29.9).tier).toBe('yellow');
    });

    it('red: +30..+60%', () => {
      expect(deviationInfo(30)).toEqual({ side: 'over', magnitudePct: 30, tier: 'red' });
      expect(deviationInfo(59.9).tier).toBe('red');
    });

    it('darkred: +60%+', () => {
      expect(deviationInfo(60)).toEqual({ side: 'over', magnitudePct: 60, tier: 'darkred' });
      expect(deviationInfo(1780).tier).toBe('darkred');
    });
  });

  describe('under (actual < prediction) — один уровень', () => {
    it('lightblue для любого недогруза ≥ 15%', () => {
      expect(deviationInfo(-15).side).toBe('under');
      expect(deviationInfo(-15).tier).toBe('unknown'); // рендерится через visualFor → lightblue
      expect(deviationInfo(-30).side).toBe('under');
      expect(deviationInfo(-60).side).toBe('under');
      expect(deviationInfo(-1780).side).toBe('under');
    });

    it('magnitude передаётся', () => {
      expect(deviationInfo(-47.5).magnitudePct).toBe(47.5);
    });
  });

  describe('normal (|dev| < 15%)', () => {
    it('green с обеих сторон', () => {
      expect(deviationInfo(0)).toEqual({ side: 'normal', magnitudePct: 0, tier: 'green' });
      expect(deviationInfo(14.9).tier).toBe('green');
      expect(deviationInfo(-14.9).tier).toBe('green');
    });
  });

  describe('unknown', () => {
    it('null / NaN / Infinity → unknown / gray', () => {
      expect(deviationInfo(null).side).toBe('unknown');
      expect(deviationInfo(null).tier).toBe('unknown');
      expect(deviationInfo(Number.NaN).side).toBe('unknown');
    });
  });
});

describe('visualFor', () => {
  it('under → lightblue', () => {
    expect(visualFor(deviationInfo(-30))).toBe(COLORS.lightblue);
    expect(visualFor(deviationInfo(-1780))).toBe(COLORS.lightblue);
  });

  it('over → yellow/red/darkred', () => {
    expect(visualFor(deviationInfo(20))).toBe(COLORS.yellow);
    expect(visualFor(deviationInfo(45))).toBe(COLORS.red);
    expect(visualFor(deviationInfo(80))).toBe(COLORS.darkred);
  });

  it('normal → green', () => {
    expect(visualFor(deviationInfo(0))).toBe(COLORS.green);
    expect(visualFor(deviationInfo(10))).toBe(COLORS.green);
    expect(visualFor(deviationInfo(-10))).toBe(COLORS.green);
  });

  it('unknown → gray', () => {
    expect(visualFor(deviationInfo(null))).toBe(COLORS.gray);
    expect(visualFor(deviationInfo(Number.NaN))).toBe(COLORS.gray);
  });
});
