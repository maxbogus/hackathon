/**
 * T-129: single-tram card for the passenger-mode grid.
 *
 * Each card has:
 *   - the route badge (top-left, e.g. "А" or "39")
 *   - the ETA in minutes (or "🚉 Ушёл" if eta_min == 0)
 *   - a load percentage gauge with a colour-coded top border:
 *
 *         load   0..70   → green   (comfortable)
 *         load  70..90   → yellow  (grey zone)
 *         load  90..110  → red     (crowded)
 *         load 110..∞    → darkred (over capacity)
 *
 * The colour thresholds match T-128's load_pct logic so the dispatcher view
 * and the passenger view stay visually consistent.
 */

import type { ETAPrediction } from './recommend';
import { loadTier, type LoadTier } from './loadTier';

export interface EtaCardProps {
  tram: ETAPrediction;
}

const BORDER_BY_TIER: Record<LoadTier, string> = {
  green: '#2e7d32',
  yellow: '#f9a825',
  red: '#c62828',
  darkred: '#7f0000',
};

const BG_BY_TIER: Record<LoadTier, string> = {
  green: '#f1f8e9',
  yellow: '#fff8e1',
  red: '#ffebee',
  darkred: '#ffcdd2',
};

export function EtaCard({ tram }: EtaCardProps): JSX.Element {
  const tier = loadTier(tram.predicted_load_pct);

  return (
    <div
      data-testid="eta-card"
      data-tier={tier}
      className={`eta-card eta-card--${tier}`}
      style={{
        borderTop: `4px solid ${BORDER_BY_TIER[tier]}`,
        background: BG_BY_TIER[tier],
        padding: '12px 16px',
        borderRadius: 6,
        minWidth: 140,
        boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
      }}
    >
      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          lineHeight: 1,
          color: BORDER_BY_TIER[tier],
        }}
      >
        {tram.route_name}
      </div>
      <div style={{ marginTop: 8, fontSize: 14, color: '#333' }}>
        {tram.eta_min === 0 ? (
          <span>🚉 Ушёл</span>
        ) : (
          <span>
            ⏱ <strong>{tram.eta_min} мин</strong>
          </span>
        )}
      </div>
      <div style={{ marginTop: 4, fontSize: 14, color: '#555' }}>
        👥 {tram.predicted_load_pct}% загрузка
      </div>
    </div>
  );
}
