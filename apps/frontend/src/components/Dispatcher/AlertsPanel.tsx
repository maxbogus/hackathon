/**
 * AlertsPanel -- dispatcher overload alerts with 60s auto-refresh.
 *
 * T-131: replaces the `PlaceholderPanel` for the dispatcher role.
 *
 * Polling: TanStack Query's `refetchInterval` does the same job as the
 * `streamlit-autorefresh` snippet in the original AC.
 *
 * T-141: every user-facing string is looked up through `t()` / `tf()` from
 * `lib/i18n`. The format-relative time stamp and the window suffix are
 * assembled lazily so an unmount mid-fetch can't reach the DOM with stale
 * text. No Russian literal leaks into this file.
 */

import { useCallback } from 'react';

import { t, tf } from '@/lib/i18n/t';

import { useGetOverloadAlertsApiV1InsightsAlertsGet } from '@/generated/api';

import { AlertCard } from './AlertCard';
import type { OverloadAlert } from '@/generated/api.schemas';

const REFETCH_INTERVAL_MS = 60_000;
const DEFAULT_WINDOW_MIN = 30;

export function AlertsPanel(): JSX.Element {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useGetOverloadAlertsApiV1InsightsAlertsGet(
      { window_min: DEFAULT_WINDOW_MIN },
      { query: { refetchInterval: REFETCH_INTERVAL_MS } },
    );

  const handleRelease = useCallback((alert: OverloadAlert) => {
    // T-131 deliberately does not wire this to a backend call --
    // a real release-tram flow is out of scope. Logging here keeps the UX
    // visible while leaving the seam obvious for follow-up work.
    // eslint-disable-next-line no-console
    console.info('[dispatcher] release tram requested', alert);
  }, []);

  if (isLoading) {
    return <p data-testid="alerts-loading">{t('dispatcher.alerts.loading')}</p>;
  }

  if (isError) {
    return (
      <section data-testid="alerts-error" role="alert">
        <p>
          {t('dispatcher.alerts.errorPrefix')} {String(error)}
        </p>
        <button type="button" onClick={() => refetch()}>
          {t('dispatcher.alerts.retry')}
        </button>
      </section>
    );
  }

  const alerts = data?.alerts ?? [];
  const generatedAt = data?.generated_at ? new Date(data.generated_at) : null;
  const windowMin = data?.window_min ?? DEFAULT_WINDOW_MIN;
  const generatedAtLabel = generatedAt?.toLocaleTimeString() ?? t('dispatcher.alerts.unknownTime');
  const updatedText = isFetching
    ? t('dispatcher.alerts.fetching')
    : tf('dispatcher.alerts.updatedAt', generatedAtLabel);

  return (
    <section style={{ padding: '16px 24px' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <h2 style={{ margin: 0 }}>{t('dispatcher.alerts.title')}</h2>
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {updatedText}
          {tf('dispatcher.alerts.windowSuffix', windowMin)}
        </span>
      </header>

      {alerts.length === 0 ? (
        <p
          data-testid="alerts-empty"
          style={{
            padding: 16,
            background: '#d1fae5',
            border: '1px solid #6ee7b7',
            borderRadius: 6,
            color: '#065f46',
          }}
        >
          {tf('dispatcher.alerts.emptyState', windowMin)}
        </p>
      ) : (
        <div data-testid="alerts-list">
          {alerts.map((alert) => (
            <AlertCard
              key={`${alert.stop_id}-${alert.route_id}-${alert.time_to_overload_min}`}
              alert={alert}
              onRelease={handleRelease}
            />
          ))}
        </div>
      )}
    </section>
  );
}
