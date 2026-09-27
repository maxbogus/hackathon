/**
 * T-218: карточка маршрута для пассажирского экрана.
 *
 * Variant 'actual' → block "Как было" (actuals).
 * Variant 'prediction' → block "Как будет" (predictions).
 *
 * Tiers (clinerule 31, синхронизировано с apps/backend/app/load_tier.py):
 *   < 70    → green    🟢
 *   70..90  → yellow   🟡
 *   90..110 → red      🟠
 *   >= 110  → darkred  🔴
 */

import { t } from '@/lib/i18n/t';

import { loadTier, type LoadTier } from '@/lib/loadTier';
import type { RouteLoadVariant } from '@/lib/routeLoad';

export interface RouteLoadCardProps {
  readonly routeId: number;
  /** null = "нет данных" (passing null ровно как в предыдущей реализации) */
  readonly loadPct: number | null;
  readonly variant?: RouteLoadVariant;
}

const BG_BY_TIER: Readonly<Record<LoadTier, string>> = {
  green: '#f1f8e9',
  yellow: '#fff8e1',
  red: '#ffebee',
  darkred: '#ffcdd2',
};

const BORDER_BY_TIER: Readonly<Record<LoadTier, string>> = {
  green: '#2e7d32',
  yellow: '#f9a825',
  red: '#c62828',
  darkred: '#7f0000',
};

const LABEL_BY_TIER: Readonly<Record<LoadTier, string>> = {
  green: '🟢',
  yellow: '🟡',
  red: '🟠',
  darkred: '🔴',
};

export function RouteLoadCard({ routeId, loadPct, variant }: RouteLoadCardProps): JSX.Element {
  const cardStyle: React.CSSProperties = {
    borderRadius: 6,
    padding: '16px 12px',
    minWidth: 130,
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 6,
  };

  if (loadPct === null) {
    return (
      <article
        data-testid="route-load-card"
        data-tier="unknown"
        data-route-id={routeId}
        data-variant={variant ?? 'prediction'}
        style={{
          ...cardStyle,
          background: '#f5f5f5',
          borderTop: '4px solid #9e9e9e',
        }}
      >
        <div style={{ fontSize: 13, color: '#555' }}>{tfRouteLabel(routeId)}</div>
        <div style={{ fontSize: 24, color: '#9e9e9e' }}>—</div>
        <div style={{ fontSize: 12, color: '#888' }}>{t('passenger.routeNoData')}</div>
      </article>
    );
  }

  const tier = loadTier(loadPct);
  const display = Math.round(loadPct);

  return (
    <article
      data-testid="route-load-card"
      data-tier={tier}
      data-route-id={routeId}
      data-variant={variant ?? 'prediction'}
      style={{
        ...cardStyle,
        background: BG_BY_TIER[tier],
        borderTop: `4px solid ${BORDER_BY_TIER[tier]}`,
      }}
    >
      <div style={{ fontSize: 13, color: '#555' }}>{tfRouteLabel(routeId)}</div>
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          lineHeight: 1,
          color: BORDER_BY_TIER[tier],
        }}
      >
        {display}%
      </div>
      <div style={{ fontSize: 13, color: '#555' }}>
        {LABEL_BY_TIER[tier]} {t(`passenger.loadTier.${tier}`)}
      </div>
    </article>
  );
}

function tfRouteLabel(routeId: number): string {
  return `Маршрут ${routeId}`;
}
