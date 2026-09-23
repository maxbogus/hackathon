/**
 * AlertsPanel -- dispatcher overload alerts with 60s auto-refresh.
 *
 * T-131: replaces the `PlaceholderPanel` for the dispatcher role.
 *
 * Polling: TanStack Query's `refetchInterval` does the same job as the
 * `streamlit-autorefresh` snippet in the original AC. We log a soft warning
 * (development only) when the hook is unmounted mid-flight.
 */

import { useCallback } from 'react';

import { useGetOverloadAlertsApiV1InsightsAlertsGet } from '@/generated/api';

import { AlertCard } from './AlertCard';
import type { OverloadAlert } from '@/generated/api.schemas';

const REFETCH_INTERVAL_MS = 60_000;

export function AlertsPanel(): JSX.Element {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useGetOverloadAlertsApiV1InsightsAlertsGet(
      { window_min: 30 },
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
    return <p data-testid="alerts-loading">Загрузка алертов…</p>;
  }

  if (isError) {
    return (
      <section data-testid="alerts-error" role="alert">
        <p>Не удалось загрузить алерты: {String(error)}</p>
        <button type="button" onClick={() => refetch()}>
          Повторить
        </button>
      </section>
    );
  }

  const alerts = data?.alerts ?? [];
  const generatedAt = data?.generated_at ? new Date(data.generated_at) : null;
  const windowMin = data?.window_min ?? 30;

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
        <h2 style={{ margin: 0 }}>🎛️ Диспетчер · алерты перегруза</h2>
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {isFetching ? 'обновление…' : `обновлено: ${generatedAt?.toLocaleTimeString() ?? '—'}`}
          {' · горизонт '}
          {windowMin}
          {' мин'}
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
          ✅ Всё в норме на ближайшие {windowMin} мин.
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
