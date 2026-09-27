/**
 * T-218: <PassengerMode> — сравнение «как было» и «как будет».
 *
 * Layout (clinerule 31):
 *   <h2>Как было (actuals)</h2>
 *   <div data-testid="actuals-grid">{...RouteLoadCard variant="actual"}</div>
 *   <h2>Как будет (predictions)</h2>
 *   <div data-testid="predictions-grid">{...RouteLoadCard variant="prediction"}</div>
 *   <LoadLegend /> — пояснение цветов
 *
 * Источники:
 *   - actuals:     GET /api/v1/historical/load  (fallback MAX period)
 *   - predictions: GET /api/v1/predictions/load (submission period)
 *
 * T-218+ (отзыв пользователя):
 *   Карточка actual получает prediction того же routeId через `predictionById`,
 *   чтобы посчитать deviation (over/under/normal). Если прогноза нет —
 *   карточка рендерится серой (unknown).
 *
 * T-122 (карта): над гридами рендерится <RouteMap> (Strategy OSM↔Yandex).
 * Геометрия — из GET /api/v1/geo/routes (T-227), цвет/толщина линии —
 * tier и load_pct из блока predictions (та же палитра, что у карточек).
 * Клик по карточке ↔ клик по линии: общий `selectedRouteId`.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

import { t, tf } from '@/lib/i18n/t';

import { Alert } from '@/lib/Alert';
import { fetchActiveModel, formatWapeScore, type ActiveModelInfo } from '@/lib/activeModel';
import { fetchRouteGeo, mergeRouteTiers, type MapRoute } from '@/lib/geoRoutes';
import { fetchAllRouteLoads, type RouteLoad } from '@/lib/routeLoad';

import { RouteMap } from '@/components/Map/MapProvider';
import { LoadLegend } from '@/components/Passenger/LoadLegend';
import { RouteLoadCard } from '@/components/Passenger/RouteLoadCard';

export function PassengerMode(): JSX.Element {
  const [actuals, setActuals] = useState<RouteLoad[]>([]);
  const [predictions, setPredictions] = useState<RouteLoad[]>([]);
  const [geoRoutes, setGeoRoutes] = useState<MapRoute[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null);
  const [activeModel, setActiveModel] = useState<ActiveModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    (async (): Promise<void> => {
      try {
        const [{ actuals: a, predictions: p }, geo] = await Promise.all([
          fetchAllRouteLoads(controller.signal),
          fetchRouteGeo(controller.signal),
        ]);
        if (controller.signal.aborted) return;
        setActuals(a);
        setPredictions(p);
        setGeoRoutes(geo);
        if (a.length === 0 && p.length === 0) {
          setError(t('passenger.routesEmpty'));
        }
      } catch (e: unknown) {
        if (!controller.signal.aborted) {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchActiveModel(controller.signal)
      .then((info) => {
        if (!controller.signal.aborted) setActiveModel(info);
      })
      .catch(() => {});
    return () => {
      controller.abort();
    };
  }, []);

  // predictionsById: routeId → boardings (для deviation в actual-карточках).
  const predictionsById = useMemo(() => {
    const m = new Map<number, number>();
    for (const p of predictions) {
      if (p.boardings !== null) m.set(p.routeId, p.boardings);
    }
    return m;
  }, [predictions]);

  // T-122: цвет/толщина маршрута на карте = tier и load_pct прогноза
  // (те же значения, что у prediction-карточек).
  const tiers = useMemo(() => mergeRouteTiers(predictions), [predictions]);

  // T-122: выбор маршрута — toggle (повторный клик снимает подсветку).
  const handleSelectRoute = useCallback((routeId: number): void => {
    setSelectedRouteId((prev) => (prev === routeId ? null : routeId));
  }, []);

  const wapeLabel = formatWapeScore(activeModel?.wape_score ?? null);
  const modelId = activeModel?.model_id ?? '\u2014';
  const footerText =
    wapeLabel !== null
      ? tf('passenger.activeModelFooter', modelId, wapeLabel)
      : tf('passenger.modelFooter', modelId);

  return (
    <section style={{ padding: '16px 24px', fontFamily: 'system-ui, sans-serif' }}>
      <h2 style={{ marginTop: 0 }}>{t('passenger.modeTitle')}</h2>
      <p style={{ color: '#666', marginTop: 4 }}>{t('passenger.modeHint')}</p>

      {error && (
        <Alert severity="warning" icon="\u26a0\ufe0f">
          {tf('passenger.etaError', error)}
        </Alert>
      )}

      {loading && <p style={{ color: '#666' }}>{t('common.loading')}</p>}

      {/* T-122: карта маршрутов (геометрия + цвет/толщина как у карточек). */}
      {!loading && (
        <RouteMap
          routes={geoRoutes}
          tierByRoute={tiers.tierByRoute}
          loadPctByRoute={tiers.loadPctByRoute}
          selectedRouteId={selectedRouteId}
          onSelectRoute={handleSelectRoute}
        />
      )}

      {!loading && actuals.length > 0 && (
        <>
          <h3 style={{ marginTop: 16, color: '#555' }}>
            {t('passenger.actualsHeader')}
          </h3>
          <div
            data-testid="actuals-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: 12,
              marginTop: 8,
            }}
          >
            {actuals.map((load) => (
              <RouteLoadCard
                key={load.routeId}
                routeId={load.routeId}
                boardings={load.boardings}
                predictionBoardings={predictionsById.get(load.routeId) ?? null}
                tier={load.tier === 'unknown' ? null : load.tier}
                loadPct={load.loadPct}
                variant="actual"
                selected={selectedRouteId === load.routeId}
                onSelect={handleSelectRoute}
              />
            ))}
          </div>
        </>
      )}

      {!loading && predictions.length > 0 && (
        <>
          <h3 style={{ marginTop: 24, color: '#555' }}>
            {t('passenger.predictionsHeader')}
          </h3>
          <div
            data-testid="predictions-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: 12,
              marginTop: 8,
            }}
          >
            {predictions.map((load) => (
              <RouteLoadCard
                key={load.routeId}
                routeId={load.routeId}
                boardings={load.boardings}
                tier={load.tier === 'unknown' ? null : load.tier}
                loadPct={load.loadPct}
                variant="prediction"
                selected={selectedRouteId === load.routeId}
                onSelect={handleSelectRoute}
              />
            ))}
          </div>
        </>
      )}

      <LoadLegend />

      <p style={{ marginTop: 16, color: '#888', fontSize: 12 }}>{footerText}</p>
    </section>
  );
}
