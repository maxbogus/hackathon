/**
 * T-230: клиент управления наборами прогнозов.
 *
 * Проверяем контракт эндпоинтов (URL/method/body) и чистые хелперы polling.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  RUN_POLL_INTERVAL_MS,
  fetchActiveSet,
  fetchRun,
  fetchRuns,
  ingestRun,
  isRunPending,
  isRunReadyToLoad,
  regeneratePredictions,
  rejectRun,
  restoreEtalon,
  type PredictionRun,
  type RunStatus,
} from './predictionRuns';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

function lastFetchCall(): { url: string; init: RequestInit } {
  const call = vi.mocked(fetch).mock.calls.at(-1);
  return {
    url: String(call?.[0] ?? ''),
    init: (call?.[1] ?? {}) as RequestInit,
  };
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ ok: true })));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('чистые хелперы', () => {
  it('RUN_POLL_INTERVAL_MS = 3000 (как у /pipeline/status)', () => {
    expect(RUN_POLL_INTERVAL_MS).toBe(3000);
  });

  it.each<RunStatus>(['running', 'queued', 'started'])('isRunPending(%s) === true', (status) => {
    expect(isRunPending(status)).toBe(true);
  });

  it.each<RunStatus>(['ready', 'loaded', 'rejected', 'failed'])(
    'isRunPending(%s) === false',
    (status) => {
      expect(isRunPending(status)).toBe(false);
    },
  );

  it('isRunReadyToLoad — только для status=ready', () => {
    const base: PredictionRun = {
      id: 1,
      celery_task_id: 't',
      status: 'ready',
      submission_id: 'ui-1',
      model_id: 'm',
      feature_set: 'with_all',
      pipeline_kind: 'predict',
      row_count: 3,
      holdout_wape_score: 0.9,
      recommendation: 'READY_TO_UPLOAD',
      error: null,
      is_etalon: false,
      is_active: false,
      csv_filename: 'x.csv',
      started_at: '2026-09-27T00:00:00Z',
      finished_at: null,
      activated_at: null,
    };
    expect(isRunReadyToLoad(base)).toBe(true);
    expect(isRunReadyToLoad({ ...base, status: 'running' })).toBe(false);
  });
});

describe('regeneratePredictions', () => {
  it('POST /predictions/regenerate с коэффициентами и датами', async () => {
    await regeneratePredictions({
      coefWeather: 1.2,
      coefEvent: 1,
      coefSeason: 0.9,
      startDate: '2025-11-01',
      endDate: '2025-12-31',
    });

    const { url, init } = lastFetchCall();
    expect(url).toBe('/api/v1/predictions/regenerate');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({
      coef_weather: 1.2,
      coef_event: 1,
      coef_season: 0.9,
      start_date: '2025-11-01',
      end_date: '2025-12-31',
    });
  });

  it('не отправляет пустые опциональные поля', async () => {
    await regeneratePredictions({ coefWeather: 1, coefEvent: 1, coefSeason: 1 });
    const body = JSON.parse(String(lastFetchCall().init.body)) as Record<string, unknown>;
    expect(body).not.toHaveProperty('model_id');
    expect(body).not.toHaveProperty('start_date');
  });
});

describe('runs / active / actions', () => {
  it('fetchRun → GET /predictions/runs/{id}', async () => {
    await fetchRun(42);
    const { url, init } = lastFetchCall();
    expect(url).toBe('/api/v1/predictions/runs/42');
    expect(init.method ?? 'GET').toBe('GET');
  });

  it('fetchRuns → GET /predictions/runs?limit=N', async () => {
    await fetchRuns(5);
    expect(lastFetchCall().url).toBe('/api/v1/predictions/runs?limit=5');
  });

  it('fetchActiveSet → GET /predictions/active', async () => {
    await fetchActiveSet();
    expect(lastFetchCall().url).toBe('/api/v1/predictions/active');
  });

  it('ingestRun → POST .../ingest c activate=true', async () => {
    await ingestRun(7);
    const { url, init } = lastFetchCall();
    expect(url).toBe('/api/v1/predictions/runs/7/ingest');
    expect(JSON.parse(String(init.body))).toEqual({ activate: true });
  });

  it('rejectRun → POST .../reject', async () => {
    await rejectRun(7);
    expect(lastFetchCall().url).toBe('/api/v1/predictions/runs/7/reject');
  });

  it('restoreEtalon → POST /predictions/restore-etalon', async () => {
    await restoreEtalon();
    expect(lastFetchCall().url).toBe('/api/v1/predictions/restore-etalon');
  });
});
