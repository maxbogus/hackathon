/**
 * AnalystDashboard — T-196: главная страница режима «Аналитик».
 *
 * Layout:
 *   ┌──────────────┬──────────────────────────────┐
 *   │ FiltersPanel │  HistoricalChart             │
 *   │              ├──────────────────────────────┤
 *   │              │  PredictionsChart            │
 *   └──────────────┴──────────────────────────────┘
 *
 *   Кнопка "Download CSV" → downloadPredictionsCsv() (apps/frontend/src/api/downloadCsv.ts)
 *
 * T-233: состояние маршрута живёт здесь (как коэффициенты и horizon/granularity).
 * Список маршрутов — `lib/routeCatalog.ts` (объединение /historical и
 * /predictions/load с фолбэком на канонические 10). Оба графика принимают
 * `routeId` пропом и держат его в `queryKey`, поэтому переключение маршрута
 * автоматически рефетчит и историю, и прогноз.
 */

import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { t, tf } from '@/lib/i18n/t';
import { CANONICAL_ROUTES, fetchRouteCatalog } from '@/lib/routeCatalog';

import { HistoricalChart } from '@/components/Charts/HistoricalChart';
import { PredictionsChart } from '@/components/Charts/PredictionsChart';
import { FiltersPanel } from '@/components/Filters/FiltersPanel';
import {
  HorizonGranularity,
  type Horizon,
  type Granularity,
} from '@/components/Filters/HorizonGranularity';

import {
  downloadPredictionsCsv,
  triggerBrowserDownload,
  type DownloadCsvParams,
} from '@/api/downloadCsv';
import { downloadPredictionsXlsx, triggerBlobDownload } from '@/api/downloadXlsx';
import { GeneratePanel } from '@/components/Analyst/GeneratePanel';
import { HowItWorks } from '@/components/Analyst/HowItWorks';

const DEFAULT_ROUTE = 7;
const DEFAULT_FROM = '2025-09-01T00:00:00';
const DEFAULT_TO = '2025-10-31T00:00:00';
const SUBMISSION_FROM = '2025-11-01T00:00:00';
const SUBMISSION_TO = '2025-12-31T23:00:00';

/** T-233: каталог маршрутов меняется только вместе с данными — как у графиков, 5 мин. */
const ROUTE_CATALOG_STALE_TIME_MS = 5 * 60_000;

export function AnalystDashboard(): JSX.Element {
  const [routeId, setRouteId] = useState<number>(DEFAULT_ROUTE);
  const [coefWeather, setCoefWeather] = useState(1.0);
  const [coefEvent, setCoefEvent] = useState(1.0);
  const [coefSeason, setCoefSeason] = useState(1.0);

  // T-203: horizon + granularity selectors. The backend
  // /api/v1/predictions/db/{route_id} (T-195) supports these — the
  // frontend was just hard-coded to (day, hour) until now.
  const [horizon, setHorizon] = useState<Horizon>('day');
  const [granularity, setGranularity] = useState<Granularity>('hour');

  // T-233: список маршрутов для селектора. `fetchRouteCatalog` не бросает, а
  // пока запрос идёт — показываем канонические 10 маршрутов, чтобы селект
  // никогда не был пустым.
  const catalogQuery = useQuery({
    queryKey: ['route-catalog'],
    queryFn: () => fetchRouteCatalog(),
    staleTime: ROUTE_CATALOG_STALE_TIME_MS,
  });

  /**
   * Опции селекта маршрута. Текущий маршрут присутствует всегда: без своей
   * `<option>` браузер сбросил бы value, и оба графика ушли бы в «нет данных».
   */
  const routeOptions = useMemo(() => {
    const base = catalogQuery.data ?? CANONICAL_ROUTES;
    return base.includes(routeId) ? base : [routeId, ...base].sort((a, b) => a - b);
  }, [catalogQuery.data, routeId]);

  const [csvStatus, setCsvStatus] = useState<string>('');
  const [xlsxStatus, setXlsxStatus] = useState<string>('');

  const handleCoefChange = (w: number, e: number, s: number) => {
    setCoefWeather(w);
    setCoefEvent(e);
    setCoefSeason(s);
  };

  /** Общие параметры экспорта для CSV и XLSX (T-228). */
  const exportParams = (): DownloadCsvParams => ({
    from: SUBMISSION_FROM,
    to: SUBMISSION_TO,
    coefWeather,
    coefEvent,
    coefSeason,
    // modelId / featureSet / zerosApplied = null → defaults (активный набор, T-230)
  });

  const handleDownloadCsv = async () => {
    setCsvStatus(t('common.loading'));
    try {
      const result = await downloadPredictionsCsv(exportParams());
      triggerBrowserDownload(result);
      setCsvStatus(tf('analyst.csvDownloaded', result.rowCount));
    } catch (err) {
      setCsvStatus(`${t('analyst.csvError')}: ${String(err)}`);
    }
  };

  /** T-228: XLSX-экспорт (бэкенд /predictions/export.xlsx, T-206). */
  const handleDownloadXlsx = async () => {
    setXlsxStatus(t('common.loading'));
    try {
      const result = await downloadPredictionsXlsx(exportParams());
      triggerBlobDownload(result);
      setXlsxStatus(tf('analyst.xlsxDownloaded', result.rowCount));
    } catch (err) {
      setXlsxStatus(`${t('analyst.xlsxError')}: ${String(err)}`);
    }
  };

  return (
    <div
      data-testid="analyst-dashboard"
      style={{
        display: 'grid',
        gridTemplateColumns: '320px 1fr',
        gap: 16,
        padding: 16,
      }}
    >
      <div>
        <FiltersPanel
          routeId={routeId}
          routes={routeOptions}
          onRouteChange={setRouteId}
          coefWeather={coefWeather}
          coefEvent={coefEvent}
          coefSeason={coefSeason}
          onCoefChange={handleCoefChange}
        />
        {/* T-230: генерация набора, активный набор, возврат эталона */}
        <GeneratePanel coefWeather={coefWeather} coefEvent={coefEvent} coefSeason={coefSeason} />
      </div>

      <section>
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 16,
          }}
        >
          <h1>{t('analyst.title')}</h1>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={handleDownloadCsv}
              data-testid="download-csv-button"
              style={{
                padding: '8px 16px',
                background: '#4f46e5',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              {t('analyst.downloadCsv')}
            </button>
            {/* T-228: XLSX-экспорт (тот же набор параметров, что у CSV) */}
            <button
              type="button"
              onClick={handleDownloadXlsx}
              data-testid="download-xlsx-button"
              style={{
                padding: '8px 16px',
                background: 'white',
                color: '#4f46e5',
                border: '1px solid #4f46e5',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              {t('analyst.downloadXlsx')}
            </button>
          </div>
        </header>

        {/* T-230: объясняем флоу, чтобы генерация не «конфьюзила» */}
        <HowItWorks />

        {csvStatus && (
          <p data-testid="csv-status" style={{ marginBottom: 8 }}>
            {csvStatus}
          </p>
        )}

        {xlsxStatus && (
          <p data-testid="xlsx-status" style={{ marginBottom: 8 }}>
            {xlsxStatus}
          </p>
        )}

        <HistoricalChart routeId={routeId} fromDate={DEFAULT_FROM} toDate={DEFAULT_TO} />

        <div style={{ margin: '16px 0' }}>
          <HorizonGranularity
            horizon={horizon}
            granularity={granularity}
            onChange={(next) => {
              setHorizon(next.horizon);
              setGranularity(next.granularity);
            }}
          />
        </div>

        <PredictionsChart
          routeId={routeId}
          fromDate={SUBMISSION_FROM}
          toDate={SUBMISSION_TO}
          horizon={horizon}
          granularity={granularity}
          coefWeather={coefWeather}
          coefEvent={coefEvent}
          coefSeason={coefSeason}
        />
      </section>
    </div>
  );
}
