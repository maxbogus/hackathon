/**
 * predictionRuns — API-клиент управления наборами прогнозов (T-230).
 *
 * Дашборд «Аналитик»: сгенерировать прогноз (Celery) → получить кандидата →
 * загрузить его в БД и сделать активным, либо оставить эталон.
 *
 * Backend: apps/backend/app/api/predictions_runs.py
 */

import { customInstance } from '@/api/customInstance';

/** Статусы lifecycle кандидата (см. clinerule 24). */
export type RunStatus =
  'running' | 'queued' | 'started' | 'ready' | 'loaded' | 'rejected' | 'failed';

export type Recommendation =
  'READY_TO_UPLOAD' | 'NEEDS_FIX' | 'WORSE_THAN_PREVIOUS' | 'IDENTICAL_TO_PREVIOUS';

export interface PredictionRun {
  readonly id: number;
  readonly celery_task_id: string;
  readonly status: RunStatus;
  readonly submission_id: string | null;
  readonly model_id: string | null;
  readonly feature_set: string | null;
  readonly pipeline_kind: string | null;
  readonly row_count: number | null;
  readonly holdout_wape_score: number | null;
  readonly recommendation: Recommendation | null;
  readonly error: string | null;
  readonly is_etalon: boolean;
  readonly is_active: boolean;
  readonly csv_filename: string | null;
  readonly started_at: string;
  readonly finished_at: string | null;
  readonly activated_at: string | null;
}

export interface PredictionRunList {
  readonly runs: PredictionRun[];
  readonly count: number;
  readonly active_submission_id: string | null;
}

export interface ActiveSet {
  readonly submission_id: string | null;
  readonly model_id: string | null;
  readonly feature_set: string | null;
  readonly zeros_applied: boolean | null;
  readonly coef_weather: number;
  readonly coef_event: number;
  readonly coef_season: number;
  readonly row_count: number;
  readonly is_etalon: boolean;
}

export interface RegenerateParams {
  readonly coefWeather: number;
  readonly coefEvent: number;
  readonly coefSeason: number;
  readonly startDate?: string;
  readonly endDate?: string;
  readonly modelId?: string;
}

export interface RegenerateResult {
  readonly run_id: number;
  readonly task_id: string;
  readonly status: RunStatus;
  readonly submission_id: string;
}

export interface RunAction {
  readonly run: PredictionRun | null;
  readonly rows: number;
  readonly active_submission_id: string | null;
  readonly message: string;
}

/** Интервал polling статуса запуска (мс) — 3с, как у /pipeline/status (T-198). */
export const RUN_POLL_INTERVAL_MS = 3000;

/** Запуск ещё выполняется? (нужен ли polling) */
export function isRunPending(status: RunStatus): boolean {
  return status === 'running' || status === 'queued' || status === 'started';
}

/** Кандидат готов к загрузке в БД? */
export function isRunReadyToLoad(run: PredictionRun): boolean {
  return run.status === 'ready';
}

export async function regeneratePredictions(params: RegenerateParams): Promise<RegenerateResult> {
  return customInstance<RegenerateResult>({
    url: '/api/v1/predictions/regenerate',
    method: 'POST',
    body: {
      coef_weather: params.coefWeather,
      coef_event: params.coefEvent,
      coef_season: params.coefSeason,
      ...(params.startDate ? { start_date: params.startDate } : {}),
      ...(params.endDate ? { end_date: params.endDate } : {}),
      ...(params.modelId ? { model_id: params.modelId } : {}),
    },
  });
}

export async function fetchRun(runId: number): Promise<PredictionRun> {
  return customInstance<PredictionRun>({
    url: `/api/v1/predictions/runs/${runId}`,
    method: 'GET',
  });
}

export async function fetchRuns(limit = 20): Promise<PredictionRunList> {
  return customInstance<PredictionRunList>({
    url: `/api/v1/predictions/runs?limit=${limit}`,
    method: 'GET',
  });
}

export async function fetchActiveSet(): Promise<ActiveSet> {
  return customInstance<ActiveSet>({
    url: '/api/v1/predictions/active',
    method: 'GET',
  });
}

/** Загрузить CSV кандидата в БД (+ сделать активным, если activate=true). */
export async function ingestRun(runId: number, activate = true): Promise<RunAction> {
  return customInstance<RunAction>({
    url: `/api/v1/predictions/runs/${runId}/ingest`,
    method: 'POST',
    body: { activate },
  });
}

/** Отклонить кандидата — активный набор не меняется. */
export async function rejectRun(runId: number): Promise<RunAction> {
  return customInstance<RunAction>({
    url: `/api/v1/predictions/runs/${runId}/reject`,
    method: 'POST',
  });
}

/** Вернуть эталонный набор активным. */
export async function restoreEtalon(): Promise<RunAction> {
  return customInstance<RunAction>({
    url: '/api/v1/predictions/restore-etalon',
    method: 'POST',
  });
}
