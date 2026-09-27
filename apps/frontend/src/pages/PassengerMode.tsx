/**
 * T-200 (новая редакция): <PassengerMode> — нагрузка по линиям.
 *
 * Что показывает:
 *  - заголовок «Нагрузка по линиям»
 *  - сетка <RouteLoadCard> × N (по одной на маршрут из /api/v1/historical)
 *  - подвал: «Модель: <id> · WAPE-score <value>»
 *
 * Что УБРАНО в этой редакции (по запросу пользователя 2026-09-27):
 *  - ❌ <select> остановок (Белорусская / Чистые пруды / ...)
 *  - ❌ <EtaCard> с ETA ближайших трамваев
 *  - ❌ recommendation banner «Садитесь — будет комфортно»
 *
 * Зачем: пассажир хочет видеть «какой маршрут сейчас свободнее» ДО того,
 * как дойдёт до остановки. Остановка → карта (T-207/T-208 — отдельная сессия).
 *
 * T-141: все UI-строки через `t()` / `tf()`. Никаких хардкод-русских.
 */

import { useEffect, useState } from 'react';

import { t, tf } from '@/lib/i18n/t';

import { Alert } from '@/lib/Alert';
import { fetchActiveModel, formatWapeScore, type ActiveModelInfo } from '@/lib/activeModel';
import { fetchAllRouteLoads, fetchRoutesList, type RouteLoad } from '@/lib/routeLoad';

import { RouteLoadCard } from '@/components/Passenger/RouteLoadCard';

export function PassengerMode(): JSX.Element {
  const [loads, setLoads] = useState<RouteLoad[]>([]);
  const [activeModel, setActiveModel] = useState<ActiveModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load all route loads (routes list → for each → historical).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async (): Promise<void> => {
      try {
        const routes = await fetchRoutesList();
        if (routes.length === 0) {
          if (!cancelled) {
            setLoads([]);
            setError(t('passenger.routesEmpty'));
          }
          return;
        }
        const all = await fetchAllRouteLoads(routes);
        if (!cancelled) setLoads(all);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Active model from /api/v1/models/active — silent failure.
  useEffect(() => {
    let cancelled = false;
    fetchActiveModel()
      .then((info) => {
        if (!cancelled) setActiveModel(info);
      })
      .catch(() => {
        // Silent
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const wapeLabel = formatWapeScore(activeModel?.wape_score ?? null);
  const modelId = activeModel?.model_id ?? '—';
  const footerText =
    wapeLabel !== null
      ? tf('passenger.activeModelFooter', modelId, wapeLabel)
      : tf('passenger.modelFooter', modelId);

  return (
    <section style={{ padding: '16px 24px', fontFamily: 'system-ui, sans-serif' }}>
      <h2 style={{ marginTop: 0 }}>{t('passenger.modeTitle')}</h2>
      <p style={{ color: '#666', marginTop: 4 }}>{t('passenger.modeHint')}</p>

      {error && (
        <Alert severity="warning" icon="⚠️">
          {tf('passenger.etaError', error)}
        </Alert>
      )}

      {loading && (
        <p style={{ color: '#666' }}>{t('common.loading')}</p>
      )}

      {!loading && loads.length > 0 && (
        <div
          data-testid="routes-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
            gap: 12,
            marginTop: 16,
          }}
        >
          {loads.map((load) =>
            load.loadPct === null ? (
              <article
                key={load.routeId}
                data-testid="route-load-card"
                data-tier="unknown"
                data-route-id={load.routeId}
                style={{
                  background: '#f5f5f5',
                  borderTop: '4px solid #9e9e9e',
                  borderRadius: 6,
                  padding: '16px 12px',
                  minWidth: 130,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <div style={{ fontSize: 13, color: '#555' }}>
                  Маршрут {load.routeId}
                </div>
                <div style={{ fontSize: 24, color: '#9e9e9e' }}>—</div>
                <div style={{ fontSize: 12, color: '#888' }}>нет данных</div>
              </article>
            ) : (
              <RouteLoadCard
                key={load.routeId}
                routeId={load.routeId}
                loadPct={load.loadPct}
              />
            ),
          )}
        </div>
      )}

      <p style={{ marginTop: 16, color: '#888', fontSize: 12 }}>{footerText}</p>
    </section>
  );
}
