/**
 * AlertCard -- one actionable dispatch alert.
 *
 * T-131: rendered by `AlertsPanel`, fed by
 * `GET /api/v1/insights/alerts` (Orval hook
 * `useGetOverloadAlertsApiV1InsightsAlertsGet`).
 *
 * Visual contract:
 *   - Severity controls the border colour (red shades, escalating).
 *   - "minutes until departure" is the primary CTA -- dispatcher acts on time.
 *   - The release-tram button is a placeholder wired to onRelease so the
 *     parent can hook it into a real backend flow later (not in T-131 scope).
 *
 * T-141: every user-facing string lives in `lib/i18n/ru-RU.ts`. Severity
 * labels and copy are resolved at render time via `t()`/`tf()` -- no
 * Russian literals leak into this file.
 */

import { t, tf } from '@/lib/i18n/t';

import type { OverloadAlert } from '@/generated/api.schemas';

export interface AlertCardProps {
  readonly alert: OverloadAlert;
  readonly onRelease?: (alert: OverloadAlert) => void;
}

const SEVERITY_COLORS: Readonly<Record<OverloadAlert['severity'], string>> = {
  critical: '#7f1d1d', // darkred
  warning: '#b91c1c', // red
  info: '#ca8a04', // yellow-700 (text-on-bg, not background)
};

/**
 * TKeys for the three severity pills. Mapping colour to key keeps the
 * lookup const-assertable, which `TKey`'s unions rely on.
 */
const SEVERITY_LABEL_KEYS = {
  critical: 'dispatcher.alerts.card.severityCritical',
  warning: 'dispatcher.alerts.card.severityWarning',
  info: 'dispatcher.alerts.card.severityInfo',
} as const satisfies Readonly<Record<OverloadAlert['severity'], `dispatcher.alerts.card.severity${'Critical' | 'Warning' | 'Info'}`>>;

function severityBackground(severity: OverloadAlert['severity']): string {
  switch (severity) {
    case 'critical':
      return '#fecaca'; // red-200
    case 'warning':
      return '#fde68a'; // amber-200
    case 'info':
      return '#fef9c3'; // yellow-100
  }
}

export function AlertCard({ alert, onRelease }: AlertCardProps): JSX.Element {
  return (
    <article
      data-testid="alert-card"
      data-severity={alert.severity}
      style={{
        border: `2px solid ${SEVERITY_COLORS[alert.severity]}`,
        borderRadius: 6,
        padding: 12,
        background: severityBackground(alert.severity),
        marginBottom: 8,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong style={{ fontSize: 16 }}>{tf('dispatcher.alerts.card.routeLabel', alert.route_name)}</strong>
        <span
          data-testid="severity-pill"
          style={{
            fontSize: 12,
            padding: '2px 8px',
            borderRadius: 999,
            background: SEVERITY_COLORS[alert.severity],
            color: '#fff',
          }}
        >
          {t(SEVERITY_LABEL_KEYS[alert.severity])}
        </span>
      </header>

      <p style={{ margin: 0, fontSize: 14 }}>
        {t('dispatcher.alerts.card.stopPrefix')} <strong>#{alert.stop_id}</strong> ·{' '}
        {t('dispatcher.alerts.card.loadPrefix')}{' '}
        <strong>{alert.predicted_load_pct.toFixed(1)}%</strong>
      </p>

      <p data-testid="time-to-overload" style={{ margin: 0, fontSize: 14, color: '#1f2937' }}>
        {tf('dispatcher.alerts.card.timeToOverload', alert.time_to_overload_min)}
      </p>

      <button
        type="button"
        onClick={() => onRelease?.(alert)}
        style={{
          marginTop: 4,
          alignSelf: 'flex-start',
          padding: '6px 12px',
          background: '#1d4ed8',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: 'pointer',
          fontSize: 13,
        }}
      >
        {t('dispatcher.alerts.card.releaseButton')}
      </button>
    </article>
  );
}
