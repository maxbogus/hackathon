/**
 * T-230: GeneratePanel — генерация, кандидат, загрузка/отклонение, эталон.
 *
 * Проверяем UI-флоу, который видит аналитик:
 *   1. активный набор (эталон) отображается сразу;
 *   2. «Сгенерировать» → POST /regenerate, затем polling → панель кандидата;
 *   3. «Загрузить и сделать активным» → POST /ingest + сообщение;
 *   4. «Оставить эталон» → POST /reject + сообщение;
 *   5. «Вернуть эталон» → POST /restore-etalon + сообщение.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GeneratePanel } from './GeneratePanel';

const ACTIVE_SET = {
  submission_id: 'seed-test-submission',
  model_id: 'test_submission_baseline',
  feature_set: 'with_all',
  zeros_applied: true,
  coef_weather: 1,
  coef_event: 1,
  coef_season: 1,
  row_count: 14640,
  is_etalon: true,
};

const READY_RUN = {
  id: 5,
  celery_task_id: 'task-5',
  status: 'ready',
  submission_id: 'ui-20260927T000000Z',
  model_id: 'xgboost_v_ui_test',
  feature_set: 'with_all',
  pipeline_kind: 'predict',
  row_count: 14640,
  holdout_wape_score: 0.91,
  recommendation: 'READY_TO_UPLOAD',
  error: null,
  is_etalon: false,
  is_active: false,
  csv_filename: 'submission_xgboost_v_ui_test_20251101_20251231_20260927T000000Z.csv',
  started_at: '2026-09-27T00:00:00Z',
  finished_at: null,
  activated_at: null,
};

interface MockOptions {
  readonly runStatus?: string;
  readonly ingestStatus?: number;
}

function mockApi(options: MockOptions = {}): void {
  const runStatus = options.runStatus ?? 'ready';
  const ingestStatus = options.ingestStatus ?? 200;

  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      const json = (payload: unknown, status = 200): Response =>
        new Response(JSON.stringify(payload), {
          status,
          headers: { 'content-type': 'application/json' },
        });

      if (url.includes('/predictions/active')) return json(ACTIVE_SET);
      if (url.includes('/predictions/regenerate')) {
        return json({
          run_id: 5,
          task_id: 'task-5',
          status: 'running',
          submission_id: READY_RUN.submission_id,
        });
      }
      if (url.includes('/predictions/runs/5/ingest')) {
        if (ingestStatus !== 200) return json({ detail: 'boom' }, ingestStatus);
        return json({
          run: READY_RUN,
          rows: 14640,
          active_submission_id: READY_RUN.submission_id,
          message: 'ingested 14640 rows',
        });
      }
      if (url.includes('/predictions/runs/5/reject')) {
        return json({
          run: { ...READY_RUN, status: 'rejected' },
          rows: 0,
          active_submission_id: ACTIVE_SET.submission_id,
          message: 'rejected',
        });
      }
      if (url.includes('/predictions/restore-etalon')) {
        return json({
          run: null,
          rows: 14640,
          active_submission_id: ACTIVE_SET.submission_id,
          message: 'etalon restored',
        });
      }
      if (url.includes('/predictions/runs/5')) {
        return json({ ...READY_RUN, status: runStatus });
      }
      throw new Error(`unexpected fetch: ${method} ${url}`);
    }),
  );
}

function renderPanel(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={client}>
      <GeneratePanel coefWeather={1} coefEvent={1} coefSeason={1} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('активный набор', () => {
  it('показывает эталон сразу после загрузки', async () => {
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId('active-set').textContent).toContain('test_submission_baseline'),
    );
    expect(screen.getByTestId('active-set-badge').textContent).toContain('эталон');
    expect(screen.getByTestId('active-set').textContent).toContain('14640');
  });
});

describe('генерация и кандидат', () => {
  it('после генерации показывает панель кандидата с вердиктом', async () => {
    renderPanel();
    fireEvent.click(await screen.findByTestId('generate-button'));

    await waitFor(() => expect(screen.getByTestId('candidate-panel')).toBeTruthy());
    const panel = screen.getByTestId('candidate-panel');
    expect(panel.textContent).toContain('0.9100');
    expect(panel.textContent).toContain('14640');
    expect(panel.textContent).toContain('Лучше текущего');
    expect(
      vi
        .mocked(fetch)
        .mock.calls.some((call) => String(call[0]).includes('/predictions/regenerate')),
    ).toBe(true);
  });

  it('показывает статус «считаем», пока run не готов', async () => {
    mockApi({ runStatus: 'running' });
    renderPanel();
    fireEvent.click(await screen.findByTestId('generate-button'));

    await waitFor(() => expect(screen.getByTestId('generate-status')).toBeTruthy());
    expect(screen.getByTestId('generate-status').textContent).toContain('pipeline-up');
    expect(screen.queryByTestId('candidate-panel')).toBeNull();
  });
});

describe('загрузка / отклонение / эталон', () => {
  it('«Загрузить и сделать активным» → ingest + сообщение', async () => {
    renderPanel();
    fireEvent.click(await screen.findByTestId('generate-button'));
    fireEvent.click(await screen.findByTestId('candidate-load-button'));

    await waitFor(() =>
      expect(screen.getByTestId('generate-message').textContent).toContain(
        'Активным стал новый набор',
      ),
    );
    const ingestCall = vi
      .mocked(fetch)
      .mock.calls.find((call) => String(call[0]).includes('/ingest'));
    expect(ingestCall).toBeDefined();
    expect(JSON.parse(String(ingestCall?.[1]?.body))).toEqual({ activate: true });
  });

  it('«Оставить эталон» → reject + сообщение', async () => {
    renderPanel();
    fireEvent.click(await screen.findByTestId('generate-button'));
    fireEvent.click(await screen.findByTestId('candidate-reject-button'));

    await waitFor(() =>
      expect(screen.getByTestId('generate-message').textContent).toContain('Кандидат отклонён'),
    );
  });

  it('«Вернуть эталон» доступна всегда и сообщает об успехе', async () => {
    renderPanel();
    fireEvent.click(await screen.findByTestId('restore-etalon-button'));

    await waitFor(() =>
      expect(screen.getByTestId('generate-message').textContent).toContain(
        'Активен эталонный набор',
      ),
    );
  });

  it('ошибка ingest показывается пользователю', async () => {
    mockApi({ ingestStatus: 422 });
    renderPanel();
    fireEvent.click(await screen.findByTestId('generate-button'));
    fireEvent.click(await screen.findByTestId('candidate-load-button'));

    await waitFor(() =>
      expect(screen.getByTestId('generate-message').textContent).toContain(
        'Не удалось загрузить кандидата',
      ),
    );
  });
});
