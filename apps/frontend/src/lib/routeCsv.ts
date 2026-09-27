/**
 * T-221: CSV parser + fetch helpers для PassengerMode (T-223).
 *
 * Заменяет AVG(value) из /predictions/load на сырые строки из
 * /predictions/export.csv и /historical/export.csv (T-220).
 * Пассажир видит SUM за день, а не среднее за час (F-099).
 *
 * Формат CSV (4 колонки, разделитель ';'):
 *   route;date;hour;value\n
 *   1;2025-11-01;0;1188.00\n
 *
 * Единый формат с /predictions/export.csv — frontend парсер один.
 *
 * См. clinerule 31.
 */

export interface PredictionRow {
  readonly routeId: number;
  readonly date: string;
  readonly hour: number;
  readonly value: number;
}
/** Та же форма что и PredictionRow — actuals и predictions оба имеют 4 поля. */
export type ActualRow = PredictionRow;

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

/**
 * Parse CSV text → array of rows. Header skipped. Malformed rows skipped.
 *
 * @param _kind kept for future divergence (predictions vs actuals); currently unused.
 */
export function parseCsv(text: string, _kind: 'prediction' | 'actual'): PredictionRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length === 0) return [];
  const out: PredictionRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(';');
    if (parts.length !== 4) continue;
    const [route, date, hourStr, val] = parts;
    const routeId = Number(route);
    const hour = Number(hourStr);
    const value = Number(val);
    if (!Number.isFinite(routeId) || !Number.isFinite(value) || !Number.isFinite(hour)) continue;
    out.push({routeId, date, hour, value});
  }
  return out;
}

async function fetchCsv(path: string, signal?: AbortSignal): Promise<PredictionRow[]> {
  try {
    const r = await fetch(`${BASE_URL.replace(/\/$/, '')}${path}`, {
      signal,
      headers: {Accept: 'text/csv'},
    });
    if (!r.ok) return [];
    return parseCsv(await r.text(), 'prediction');
  } catch {
    return [];
  }
}

export function fetchPredictionsCsv(signal?: AbortSignal): Promise<PredictionRow[]> {
  return fetchCsv('/predictions/export.csv', signal);
}

export function fetchActualsCsv(signal?: AbortSignal): Promise<PredictionRow[]> {
  return fetchCsv('/historical/export.csv', signal);
}
