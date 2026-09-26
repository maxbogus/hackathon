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
 */

import { useState } from 'react';

import { t, tf } from '@/lib/i18n/t';

import { HistoricalChart } from '@/components/Charts/HistoricalChart';
import { PredictionsChart } from '@/components/Charts/PredictionsChart';
import { FiltersPanel } from '@/components/Filters/FiltersPanel';

import {
  downloadPredictionsCsv,
  triggerBrowserDownload,
  type DownloadCsvParams,
} from '@/api/downloadCsv';

const DEFAULT_ROUTE = 7;
const DEFAULT_FROM = '2025-09-01T00:00:00';
const DEFAULT_TO = '2025-10-31T00:00:00';
const SUBMISSION_FROM = '2025-11-01T00:00:00';
const SUBMISSION_TO = '2025-12-31T23:00:00';

export function AnalystDashboard(): JSX.Element {
  const [routeId] = useState<number>(DEFAULT_ROUTE);
  const [coefWeather, setCoefWeather] = useState(1.0);
  const [coefEvent, setCoefEvent] = useState(1.0);
  const [coefSeason, setCoefSeason] = useState(1.0);

  const [csvStatus, setCsvStatus] = useState<string>('');

  const handleCoefChange = (w: number, e: number, s: number) => {
    setCoefWeather(w);
    setCoefEvent(e);
    setCoefSeason(s);
  };

  const handleDownloadCsv = async () => {
    setCsvStatus(t('common.loading'));
    try {
      const params: DownloadCsvParams = {
        from: SUBMISSION_FROM,
        to: SUBMISSION_TO,
        coefWeather,
        coefEvent,
        coefSeason,
        // modelId / featureSet / zerosApplied = null → defaults from DB (best F-083)
      };
      const result = await downloadPredictionsCsv(params);
      triggerBrowserDownload(result);
      setCsvStatus(tf('analyst.csvDownloaded', result.rowCount));
    } catch (err) {
      setCsvStatus(`${t('analyst.csvError')}: ${String(err)}`);
    }
  };

  return (
    <main
      data-testid="analyst-dashboard"
      style={{
        display: 'grid',
        gridTemplateColumns: '320px 1fr',
        gap: 16,
        padding: 16,
      }}
    >
      <FiltersPanel
        routeId={routeId}
        coefWeather={coefWeather}
        coefEvent={coefEvent}
        coefSeason={coefSeason}
        onCoefChange={handleCoefChange}
      />

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
        </header>

        {csvStatus && (
          <p data-testid="csv-status" style={{ marginBottom: 8 }}>
            {csvStatus}
          </p>
        )}

        <HistoricalChart routeId={routeId} fromDate={DEFAULT_FROM} toDate={DEFAULT_TO} />

        <PredictionsChart
          routeId={routeId}
          fromDate={SUBMISSION_FROM}
          toDate={SUBMISSION_TO}
          coefWeather={coefWeather}
          coefEvent={coefEvent}
          coefSeason={coefSeason}
        />
      </section>
    </main>
  );
}
