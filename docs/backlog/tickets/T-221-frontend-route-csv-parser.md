---
id: T-221
phase: 4
title: Frontend routeCsv.ts — парсер CSV + fetch helpers
priority: P0
effort: 1
unit: hours
rice:
  R: 2
  I: 1
  C: 0.9
  score: 6.0
depends_on: [T-220]
blocks: [T-222, T-223]
tags: [frontend, csv, passenger, clinerule-31]
status: ready
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-220 добавил `/api/v1/historical/export.csv`. Уже есть `/api/v1/predictions/export.csv` (T-218).
Теперь нужен **единый типизированный парсер** для обоих endpoint'ов + fetch-helpers, чтобы
PassengerMode (T-223) мог загрузить сырой CSV и сам агрегировать SUM по маршруту за день
(вместо ложного AVG из `/predictions/load` — F-099).

CSV-формат: `route;date;hour;value\n` (4 колонки, без кавычек, разделитель `;`, header первая строка, **единый формат с predictions**).

## Acceptance Criteria

- [ ] `apps/frontend/src/lib/routeCsv.ts` создан
- [ ] `parseCsv(text, kind)` возвращает `PredictionRow[]` (header skipped, malformed rows skipped)
- [ ] `fetchPredictionsCsv()` → `Promise<PredictionRow[]>` (GET /api/v1/predictions/export.csv)
- [ ] `fetchActualsCsv()` → `Promise<ActualRow[]>` (GET /api/v1/historical/export.csv)
- [ ] Fetch helpers возвращают `[]` при HTTP error или network error (не throw)
- [ ] AbortSignal поддерживается (для cancellation в useEffect)
- [ ] vitest 7+ passed (`routeCsv.test.ts`)
- [ ] `yarn typecheck` 0 errors

## RED (apps/frontend/src/lib/routeCsv.test.ts)

```ts
import { describe, expect, it, vi } from 'vitest';
import { parseCsv, fetchPredictionsCsv } from './routeCsv';

describe('parseCsv', () => {
  it('parses single data row', () => {
    expect(parseCsv('1;2025-11-01;0;1188.00\n', 'prediction'))
      .toEqual([{routeId: 1, date: '2025-11-01', hour: 0, value: 1188.0}]);
  });
  it('ignores header row', () => {
    const csv = 'route;period_start;period_end;value\n1;a;b;1188.00\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(1);
  });
  it('returns [] for empty input', () => {
    expect(parseCsv('', 'prediction')).toEqual([]);
    expect(parseCsv('\n', 'prediction')).toEqual([]);
  });
  it('handles header-only', () => {
    expect(parseCsv('route;period_start;period_end;value\n', 'prediction')).toEqual([]);
  });
  it('parses many rows', () => {
    const csv = 'route;period_start;period_end;value\n1;a;b;100.5\n2;c;d;200.5\n3;e;f;300.5\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(3);
  });
  it('skips malformed rows', () => {
    const csv = 'route;period_start;period_end;value\n1;a;b\n2;c;d;200.5\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(1);
  });
  it('handles CRLF', () => {
    const csv = 'route;period_start;period_end;value\r\n1;a;b;100\r\n2;c;d;200\r\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(2);
  });
});

describe('fetchPredictionsCsv', () => {
  it('returns parsed array on 200', async () => {
    global.fetch = vi.fn(() => Promise.resolve(
      new Response('route;period_start;period_end;value\n1;a;b;1188\n', {status: 200}),
    ));
    const rows = await fetchPredictionsCsv();
    expect(rows).toHaveLength(1);
    expect(rows[0].routeId).toBe(1);
  });
  it('returns [] on 500', async () => {
    global.fetch = vi.fn(() => Promise.resolve(new Response('boom', {status: 500})));
    expect(await fetchPredictionsCsv()).toEqual([]);
  });
  it('returns [] on network error', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('network')));
    expect(await fetchPredictionsCsv()).toEqual([]);
  });
});
```

## GREEN (apps/frontend/src/lib/routeCsv.ts)

```ts
/**
 * T-221: CSV parser + fetch helpers для PassengerMode (T-223).
 * Заменяет AVG(value) из /predictions/load на сырые строки из CSV.
 */
export interface PredictionRow {
  readonly routeId: number;
  readonly period_start: string;
  readonly period_end: string;
  readonly hour: number;
  readonly value: number;
}
export type ActualRow = PredictionRow;

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

export function parseCsv(text: string, _kind: 'prediction' | 'actual'): PredictionRow[] {
  const lines = text.split(/\r?\n/).filter(l => l.length > 0);
  if (lines.length <= 1) return [];
  const out: PredictionRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(';');
    if (parts.length !== 4) continue;
    const [route, ps, pe, val] = parts;
    const routeId = Number(route);
    const value = Number(val);
    if (!Number.isFinite(routeId) || !Number.isFinite(value)) continue;
    out.push({routeId, period_start: ps, period_end: pe, hour: extractHour(ps), value});
  }
  return out;
}

function extractHour(iso: string): number {
  const m = iso.match(/T(\d{2})/);
  return m ? Number(m[1]) : 0;
}

async function fetchCsv(path: string, signal?: AbortSignal): Promise<PredictionRow[]> {
  try {
    const r = await fetch(`${BASE_URL.replace(/\/$/, '')}${path}`, {signal, headers: {Accept: 'text/csv'}});
    if (!r.ok) return [];
    return parseCsv(await r.text(), 'prediction');
  } catch { return []; }
}

export function fetchPredictionsCsv(signal?: AbortSignal): Promise<PredictionRow[]> {
  return fetchCsv('/predictions/export.csv', signal);
}

export function fetchActualsCsv(signal?: AbortSignal): Promise<PredictionRow[]> {
  return fetchCsv('/historical/export.csv', signal);
}
```

## Verification

```bash
cd /home/maxbogus/Repositories/hackathon/apps/frontend && yarn test:run src/lib/routeCsv.test.ts
# ожидаем: 10/10 passed
yarn typecheck
```
