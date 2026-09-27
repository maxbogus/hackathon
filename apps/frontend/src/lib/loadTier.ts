/**
 * T-129: colour-tier mapping for predicted passenger load.
 *
 * Lives in its own file (not in EtaCard.tsx) so that EtaCard.tsx only exports
 * React components — required by eslint-plugin-react-refresh for fast refresh
 * to work during `yarn dev`.
 *
 * Bucket boundaries (chosen in T-128):
 *   load < 70          → green   (comfortable)
 *   load 70..90        → yellow  (grey zone)
 *   load 90..110       → red     (crowded)
 *   load 110..∞        → darkred (over capacity)
 *
 * T-218+ — асимметричная шкала для пассажирского экрана (отзыв пользователя).
 *   Перегруз (actual > prediction):
 *     +15..+30%  → yellow
 *     +30..+60%  → red
 *     +60%+      → darkred
 *   Недогруз (actual < prediction, magnitude ≥ 15%):
 *     → lightblue (ОДИН уровень — info, не warning)
 *   Норма (|dev| < 15%):
 *     → green
 *   Нет данных / деление на 0:
 *     → unknown (рендерится как gray)
 *
 *   loadTier() остаётся для AnalystDashboard (load_pct vs TRAM_CAPACITY).
 *   deviationInfo() — для PassengerMode.
 */

export type LoadTier = 'green' | 'yellow' | 'red' | 'darkred';

export type LoadSide = 'over' | 'under' | 'normal' | 'unknown';

export interface DeviationInfo {
  readonly side: LoadSide;
  readonly magnitudePct: number;
  /** Tier для рендеринга. Для 'under' = 'unknown' (рендерится lightblue). */
  readonly tier: LoadTier | 'unknown';
}

export function loadTier(loadPct: number): LoadTier {
  if (loadPct < 70) return 'green';
  if (loadPct < 90) return 'yellow';
  if (loadPct < 110) return 'red';
  return 'darkred';
}

/**
 * Относительное отклонение actual от prediction, в процентах.
 * Возвращает null если что-то не определено или деление на 0.
 *
 * Пример: actual=120, prediction=100 → +20%
 *         actual=80,  prediction=100 → -20%
 */
export function computeDeviation(actual: number | null, prediction: number | null): number | null {
  if (actual === null || prediction === null) return null;
  if (!Number.isFinite(actual) || !Number.isFinite(prediction)) return null;
  if (prediction === 0) return null;
  return ((actual - prediction) / prediction) * 100;
}

/**
 * Асимметричная шкала отклонения (T-218+).
 * Возвращает side+magnitude+tier — карточка сама решает что рисовать.
 */
export function deviationInfo(deviationPct: number | null): DeviationInfo {
  if (deviationPct === null || !Number.isFinite(deviationPct)) {
    return { side: 'unknown', magnitudePct: 0, tier: 'unknown' };
  }
  const magnitude = Math.abs(deviationPct);
  if (magnitude < 15) {
    return { side: 'normal', magnitudePct: magnitude, tier: 'green' };
  }
  if (deviationPct > 0) {
    if (magnitude < 30) return { side: 'over', magnitudePct: magnitude, tier: 'yellow' };
    if (magnitude < 60) return { side: 'over', magnitudePct: magnitude, tier: 'red' };
    return { side: 'over', magnitudePct: magnitude, tier: 'darkred' };
  }
  // under: один уровень, рендерится через lightblue (см. COLORS).
  return { side: 'under', magnitudePct: magnitude, tier: 'unknown' };
}

/**
 * Палитра для карточек и легенды (T-218+).
 * Расширена lightblue (underload) и gray (нет данных).
 */
export interface TierVisual {
  readonly bg: string;
  readonly border: string;
  readonly label: string;
  readonly text: string;
}

export const COLORS: Readonly<Record<LoadTier | 'lightblue' | 'gray', TierVisual>> = {
  green:     { bg: '#f1f8e9', border: '#2e7d32', label: '🟢', text: 'в норме' },
  yellow:    { bg: '#fff8e1', border: '#f9a825', label: '🟡', text: '+15..+30%' },
  red:       { bg: '#ffebee', border: '#c62828', label: '🟠', text: '+30..+60%' },
  darkred:   { bg: '#ffcdd2', border: '#7f0000', label: '🔴', text: 'перегруз' },
  lightblue: { bg: '#e3f2fd', border: '#1565c0', label: '🔵', text: 'недогруз' },
  gray:      { bg: '#f5f5f5', border: '#9e9e9e', label: '⚪', text: 'нет данных' },
};

/**
 * Резолвер визуала по DeviationInfo — единая точка для карточки и легенды.
 */
export function visualFor(info: DeviationInfo): TierVisual {
  if (info.side === 'unknown') return COLORS.gray;
  if (info.side === 'under') return COLORS.lightblue;
  if (info.side === 'normal') return COLORS.green;
  return COLORS[info.tier as LoadTier];
}
