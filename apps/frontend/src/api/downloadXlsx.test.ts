/**
 * T-228: XLSX-экспорт — downloadPredictionsXlsx + triggerBlobDownload.
 *
 * Бэкенд-эндпоинт /api/v1/predictions/export.xlsx существовал (T-206),
 * но UI-кнопки не было. Проверяем: бинарный ответ (blob), парсинг headers
 * (filename/row count), общий билдер query-строки с CSV и сам триггер скачивания.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { buildExportQuery } from './downloadCsv';
import { downloadPredictionsXlsx, triggerBlobDownload } from './downloadXlsx';

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

function mockXlsxResponse(rowCount = 14640, filename = 'submission_x.xlsx'): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response('PK\u0003\u0004fake-xlsx', {
        status: 200,
        headers: {
          'content-type': XLSX_MIME,
          'content-disposition': `attachment; filename="${filename}"`,
          'x-row-count': String(rowCount),
        },
      }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('buildExportQuery — общий билдер для CSV/XLSX (DRY)', () => {
  it('собирает только заданные параметры', () => {
    const qs = buildExportQuery({
      from: '2025-11-01T00:00:00',
      to: '2025-12-31T23:00:00',
      coefWeather: 1.2,
      zerosApplied: true,
      modelId: 'xgboost_v_ui',
    });
    expect(qs).toContain('from=2025-11-01T00%3A00%3A00');
    expect(qs).toContain('coef_weather=1.2');
    expect(qs).toContain('zeros_applied=true');
    expect(qs).toContain('model_id=xgboost_v_ui');
    expect(qs).not.toContain('feature_set');
  });
});

describe('downloadPredictionsXlsx', () => {
  beforeEach(() => {
    mockXlsxResponse();
  });

  it('запрашивает /predictions/export.xlsx и возвращает blob + headers', async () => {
    const result = await downloadPredictionsXlsx({
      from: '2025-11-01T00:00:00',
      to: '2025-12-31T23:00:00',
      coefWeather: 1,
      coefEvent: 1,
      coefSeason: 1,
    });

    const calledUrl = (vi.mocked(fetch).mock.calls[0]?.[0] ?? '') as string;
    expect(calledUrl).toContain('/api/v1/predictions/export.xlsx?');
    expect(calledUrl).toContain('coef_weather=1');

    expect(result.filename).toBe('submission_x.xlsx');
    expect(result.rowCount).toBe(14640);
    expect(result.blob).toBeInstanceOf(Blob);
  });

  it('падает с понятной ошибкой на HTTP 500', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('boom', { status: 500 })));
    await expect(
      downloadPredictionsXlsx({
        from: '2025-11-01T00:00:00',
        to: '2025-12-31T23:00:00',
      }),
    ).rejects.toThrow(/HTTP 500/);
  });
});

describe('triggerBlobDownload', () => {
  it('создаёт ссылку с blob-URL и кликает по ней', () => {
    const createObjectURL = vi.fn(() => 'blob:mock-url');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);

    triggerBlobDownload({
      filename: 'submission_y.xlsx',
      rowCount: 3,
      blob: new Blob(['PK'], { type: XLSX_MIME }),
    });

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});
