/**
 * downloadCsv — скачивает CSV с /api/v1/predictions/export.csv.
 *
 * T-196 / T-197: использует orval fetch wrapper + передаёт текущие фильтры
 * (model_id, feature_set, zeros_applied, coefs). При успехе возвращает
 * { rowCount, md5 } — md5 нужен для теста "скачанный CSV == best submission".
 */

import { customInstance } from '@/generated/customInstance';

export interface DownloadCsvParams {
  from: string;        // ISO datetime
  to: string;
  modelId?: string | null;
  featureSet?: string | null;
  zerosApplied?: boolean | null;
  coefWeather?: number;
  coefEvent?: number;
  coefSeason?: number;
}

export interface DownloadCsvResult {
  filename: string;
  rowCount: number;
  md5: string;
  content: string;
}

function buildQuery(p: DownloadCsvParams): string {
  const usp = new URLSearchParams();
  usp.set('from', p.from);
  usp.set('to', p.to);
  if (p.modelId != null) usp.set('model_id', p.modelId);
  if (p.featureSet != null) usp.set('feature_set', p.featureSet);
  if (p.zerosApplied != null) {
    usp.set('zeros_applied', p.zerosApplied ? 'true' : 'false');
  }
  if (p.coefWeather != null) usp.set('coef_weather', String(p.coefWeather));
  if (p.coefEvent != null) usp.set('coef_event', String(p.coefEvent));
  if (p.coefSeason != null) usp.set('coef_season', String(p.coefSeason));
  return usp.toString();
}

/**
 * Скачивает CSV и парсит response headers.
 *
 * Использует orval customInstance (с BASE_URL + авторизацией если есть).
 */
export async function downloadPredictionsCsv(
  params: DownloadCsvParams,
): Promise<DownloadCsvResult> {
  const qs = buildQuery(params);
  const url = `/api/v1/predictions/export.csv?${qs}`;

  const response = await customInstance<string>({
    url,
    method: 'GET',
    responseType: 'text',
    headers: { Accept: 'text/csv' },
  });

  const contentDisposition = response.headers?.['content-disposition'] ?? '';
  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
  const filename = filenameMatch?.[1] ?? 'submission.csv';

  return {
    filename,
    rowCount: Number(response.headers?.['x-row-count'] ?? 0),
    md5: response.headers?.['x-csv-md5'] ?? '',
    content: String(response.data ?? ''),
  };
}

/**
 * Триггерит скачивание в браузере (через Blob URL).
 */
export function triggerBrowserDownload(result: DownloadCsvResult): void {
  const blob = new Blob([result.content], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = result.filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
