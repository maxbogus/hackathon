/**
 * downloadXlsx — скачивает XLSX с /api/v1/predictions/export.xlsx.
 *
 * T-228/T-230: тот же набор параметров, что у CSV (model_id, feature_set,
 * zeros_applied, coef_*), но бинарный ответ → Blob + triggerBlobDownload().
 * Использует общий buildExportQuery() из downloadCsv.ts (DRY).
 */

import { buildExportQuery, type DownloadCsvParams } from '@/api/downloadCsv';
import { customInstance, lastResponse } from '@/api/customInstance';

export interface DownloadXlsxResult {
  filename: string;
  rowCount: number;
  blob: Blob;
}

const DEFAULT_FILENAME = 'submission.xlsx';

function parseFilename(contentDisposition: string): string {
  const match = /filename="?([^"]+)"?/.exec(contentDisposition);
  return match?.[1] ?? DEFAULT_FILENAME;
}

/**
 * Скачивает XLSX и парсит response headers (X-Row-Count, Content-Disposition).
 */
export async function downloadPredictionsXlsx(
  params: DownloadCsvParams,
): Promise<DownloadXlsxResult> {
  const qs = buildExportQuery(params);
  const blob = await customInstance<Blob>({
    url: `/api/v1/predictions/export.xlsx?${qs}`,
    method: 'GET',
    responseType: 'blob',
  });

  const headers = lastResponse()?.headers ?? {};
  return {
    filename: parseFilename(headers['content-disposition'] ?? ''),
    rowCount: Number(headers['x-row-count'] ?? 0),
    blob,
  };
}

/**
 * Триггерит скачивание бинарного файла в браузере (Blob URL).
 */
export function triggerBlobDownload(result: DownloadXlsxResult): void {
  const url = URL.createObjectURL(result.blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = result.filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
