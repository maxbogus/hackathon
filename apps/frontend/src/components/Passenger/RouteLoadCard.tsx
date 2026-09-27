/**
 * T-200 (новая редакция): карточка маршрута для пассажирского экрана.
 *
 * Что показывает:
 *  - большой номер маршрута (слева)
 *  - процент загрузки (справа)
 *  - цветной фон по шкале loadTier (4 уровня):
 *      green   < 70    → комфортно
 *      yellow  70..90  → умеренно
 *      red     90..110 → тесно
 *      darkred 110..∞  → перегруз
 *
 * Без действий (passenger-mode — read-only), без EtaCard (тот был для ETA
 * ближайших трамваев на конкретной остановке; здесь — нагрузка по линии
 * целиком).
 */

import { t } from '@/lib/i18n/t';

import { loadTier, type LoadTier } from '@/lib/loadTier';

export interface RouteLoadCardProps {
  readonly routeId: number;
  readonly loadPct: number;
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

export function RouteLoadCard({ routeId, loadPct }: RouteLoadCardProps): JSX.Element {
  const tier = loadTier(loadPct);
  const display = Math.round(loadPct);

  return (
    <article
      data-testid="route-load-card"
      data-tier={tier}
      data-route-id={routeId}
      style={{
        background: BG_BY_TIER[tier],
        borderTop: `4px solid ${BORDER_BY_TIER[tier]}`,
        borderRadius: 6,
        padding: '16px 12px',
        minWidth: 130,
        boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 6,
      }}
    >
      <div style={{ fontSize: 13, color: '#555' }}>
        {tfRouteLabel(routeId)}
      </div>
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
