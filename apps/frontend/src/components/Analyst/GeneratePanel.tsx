/**
 * GeneratePanel — генерация прогноза, кандидат, активный набор, эталон (T-230).
 *
 * Флоу (см. «Как это работает» на том же экране):
 *   1. ▶️ «Сгенерировать прогноз» → Celery считает новый набор (кандидат).
 *   2. Когда расчёт завершён — показываем файл/строки/WAPE-score + вердикт.
 *   3. «Загрузить и сделать активным» подменяет текущие прогнозы,
 *      «Оставить эталон» — отклоняет кандидата.
 *   4. «Вернуть эталон» доступна всегда (строки в БД не удаляются).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import type { TKey } from '@/lib/i18n/keys';
import { t, tf } from '@/lib/i18n/t';
import {
  RUN_POLL_INTERVAL_MS,
  fetchActiveSet,
  fetchRun,
  ingestRun,
  isRunPending,
  regeneratePredictions,
  rejectRun,
  restoreEtalon,
  type PredictionRun,
  type Recommendation,
} from '@/lib/predictionRuns';

const RECOMMENDATION_KEYS: Record<Recommendation, TKey> = {
  READY_TO_UPLOAD: 'analyst.recommendationReady',
  WORSE_THAN_PREVIOUS: 'analyst.recommendationWorse',
  IDENTICAL_TO_PREVIOUS: 'analyst.recommendationIdentical',
  NEEDS_FIX: 'analyst.recommendationNeedsFix',
};

const buttonStyle = {
  padding: '6px 10px',
  borderRadius: 4,
  border: '1px solid #4f46e5',
  background: '#4f46e5',
  color: 'white',
  cursor: 'pointer',
  width: '100%',
} as const;

const outlineButtonStyle = {
  ...buttonStyle,
  background: 'white',
  color: '#4f46e5',
} as const;

function formatScore(value: number | null): string {
  return value === null ? '—' : value.toFixed(4);
}

function recommendationText(run: PredictionRun): string {
  return run.recommendation ? t(RECOMMENDATION_KEYS[run.recommendation]) : '';
}

interface GeneratePanelProps {
  readonly coefWeather: number;
  readonly coefEvent: number;
  readonly coefSeason: number;
}

const INVALIDATE_KEYS = [
  'predictions-active',
  'predictions-db',
  'predictions-load',
  'prediction-run',
] as const;

/**
 * Панель генерации набора прогнозов + статус кандидата.
 */
export function GeneratePanel({
  coefWeather,
  coefEvent,
  coefSeason,
}: GeneratePanelProps): JSX.Element {
  const queryClient = useQueryClient();
  const [runId, setRunId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);
  const [message, setMessage] = useState('');

  const activeQuery = useQuery({
    queryKey: ['predictions-active'],
    queryFn: fetchActiveSet,
    refetchInterval: 30_000,
  });

  const runQuery = useQuery({
    queryKey: ['prediction-run', runId],
    queryFn: () => fetchRun(runId as number),
    enabled: runId !== null,
    refetchInterval: polling ? RUN_POLL_INTERVAL_MS : false,
  });

  const run = runQuery.data ?? null;

  // Останавливаем polling, как только run вышел из pending-статуса.
  useEffect(() => {
    if (run && !isRunPending(run.status)) {
      setPolling(false);
    }
  }, [run]);

  const invalidatePredictions = () => {
    for (const key of INVALIDATE_KEYS) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
  };

  const regenerate = useMutation({
    mutationFn: () => regeneratePredictions({ coefWeather, coefEvent, coefSeason }),
    onSuccess: (res) => {
      setRunId(res.run_id);
      setPolling(true);
      setMessage('');
      queryClient.invalidateQueries({ queryKey: ['prediction-run'] });
    },
    onError: (error) => setMessage(`${t('analyst.generateError')}: ${String(error)}`),
  });

  const load = useMutation({
    mutationFn: () => ingestRun(run?.id ?? 0, true),
    onSuccess: (res) => {
      setMessage(tf('analyst.candidateLoaded', res.rows));
      invalidatePredictions();
    },
    onError: (error) => setMessage(`${t('analyst.candidateLoadError')}: ${String(error)}`),
  });

  const reject = useMutation({
    mutationFn: () => rejectRun(run?.id ?? 0),
    onSuccess: () => {
      setMessage(t('analyst.candidateRejected'));
      invalidatePredictions();
    },
  });

  const restore = useMutation({
    mutationFn: () => restoreEtalon(),
    onSuccess: () => {
      setMessage(t('analyst.restoreEtalonDone'));
      invalidatePredictions();
    },
    onError: (error) => setMessage(`${t('analyst.restoreEtalonError')}: ${String(error)}`),
  });

  const active = activeQuery.data;
  const needsFix = run?.recommendation === 'NEEDS_FIX';
  const busy = regenerate.isPending || polling;

  return (
    <div
      data-testid="generate-panel"
      style={{ marginTop: 16, padding: 16, border: '1px solid #ddd' }}
    >
      <h3>{t('analyst.generateTitle')}</h3>

      <p data-testid="active-set" style={{ fontSize: 13, margin: '4px 0' }}>
        <strong>{t('analyst.activeSetTitle')}</strong>: {active?.model_id ?? '—'}{' '}
        <em data-testid="active-set-badge">
          (
          {active?.is_etalon
            ? t('analyst.activeSetEtalonBadge')
            : t('analyst.activeSetGeneratedBadge')}
          )
        </em>
        <br />
        {t('analyst.activeSetRows')}: {active?.row_count ?? 0} · {active?.feature_set ?? '—'}
        {active?.zeros_applied ? ' · zeros=ON' : ''}
      </p>

      <button
        type="button"
        data-testid="generate-button"
        onClick={() => regenerate.mutate()}
        disabled={busy}
        style={buttonStyle}
      >
        {t('analyst.generateButton')}
      </button>

      {busy && (
        <p data-testid="generate-status" style={{ fontSize: 13, color: '#92400e' }}>
          {t('analyst.generateRunning')}
          {run ? ` (${tf('analyst.runStatusLabel', run.status)})` : ''}
          <br />
          <small>{t('analyst.generateWorkerHint')}</small>
        </p>
      )}

      {run?.status === 'failed' && (
        <p data-testid="candidate-failed" style={{ fontSize: 13, color: '#b91c1c' }}>
          {t('analyst.candidateFailed')}: {run.error ?? '—'}
        </p>
      )}

      {run?.status === 'ready' && (
        <div
          data-testid="candidate-panel"
          style={{ marginTop: 8, padding: 8, background: '#f5f3ff', borderRadius: 4 }}
        >
          <strong>{t('analyst.candidateTitle')}</strong>
          <div style={{ fontSize: 13 }}>
            {t('analyst.candidateFile')}: {run.csv_filename ?? '—'}
            <br />
            {t('analyst.candidateRows')}: {run.row_count ?? 0}
            <br />
            {t('analyst.activeSetHoldout')}: {formatScore(run.holdout_wape_score)}
          </div>
          <p style={{ fontSize: 13, margin: '6px 0' }}>{recommendationText(run)}</p>
          {needsFix && (
            <p style={{ fontSize: 12, color: '#b91c1c' }}>{t('analyst.candidateNeedsFix')}</p>
          )}
          <button
            type="button"
            data-testid="candidate-load-button"
            onClick={() => load.mutate()}
            disabled={needsFix || load.isPending}
            style={{ ...buttonStyle, marginBottom: 6 }}
          >
            {t('analyst.candidateLoadButton')}
          </button>
          <button
            type="button"
            data-testid="candidate-reject-button"
            onClick={() => reject.mutate()}
            disabled={reject.isPending}
            style={outlineButtonStyle}
          >
            {t('analyst.candidateRejectButton')}
          </button>
        </div>
      )}

      <button
        type="button"
        data-testid="restore-etalon-button"
        onClick={() => restore.mutate()}
        disabled={restore.isPending}
        style={{ ...outlineButtonStyle, marginTop: 8 }}
      >
        {t('analyst.restoreEtalonButton')}
      </button>

      {message && (
        <p data-testid="generate-message" style={{ fontSize: 13, marginTop: 8 }}>
          {message}
        </p>
      )}
    </div>
  );
}
