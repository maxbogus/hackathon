/**
 * T-221: тесты для CSV parser + fetch helpers.
 *
 * RED: эти тесты должны были упасть ДО реализации parseCsv/fetch*.
 * GREEN: они проходят после реализации в routeCsv.ts.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchActualsCsv, fetchPredictionsCsv, parseCsv } from './routeCsv';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('parseCsv', () => {
  it('parses single data row', () => {
    expect(parseCsv('1;2025-11-01;0;1188.00\n', 'prediction')).toEqual([
      {routeId: 1, date: '2025-11-01', hour: 0, value: 1188.0},
    ]);
  });

  it('ignores header row', () => {
    const csv = 'route;date;hour;value\n1;2025-11-01;0;1188.00\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(1);
  });

  it('returns [] for empty input', () => {
    expect(parseCsv('', 'prediction')).toEqual([]);
    expect(parseCsv('\n', 'prediction')).toEqual([]);
  });

  it('handles header-only (no data rows)', () => {
    expect(parseCsv('route;date;hour;value\n', 'prediction')).toEqual([]);
  });

  it('parses many rows', () => {
    const csv =
      'route;date;hour;value\n' +
      '1;2025-11-01;0;100.5\n' +
      '2;2025-11-01;1;200.5\n' +
      '3;2025-11-01;2;300.5\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(3);
    expect(parseCsv(csv, 'prediction')[0]).toEqual({
      routeId: 1,
      date: '2025-11-01',
      hour: 0,
      value: 100.5,
    });
  });

  it('skips malformed rows (less than 4 columns)', () => {
    const csv = 'route;date;hour;value\n1;2025-11-01;0\n2;2025-11-01;1;200.5\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(1);
  });

  it('skips rows with non-numeric values', () => {
    const csv =
      'route;date;hour;value\n' +
      'foo;2025-11-01;0;100\n' +
      '1;2025-11-01;0;bar\n' +
      '2;2025-11-01;0;200\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(1);
  });

  it('handles CRLF line endings', () => {
    const csv =
      'route;date;hour;value\r\n' +
      '1;2025-11-01;0;100\r\n' +
      '2;2025-11-01;1;200\r\n';
    expect(parseCsv(csv, 'prediction')).toHaveLength(2);
  });

  it('handles integer values', () => {
    expect(parseCsv('1;2025-11-01;0;1234\n', 'prediction')).toEqual([
      {routeId: 1, date: '2025-11-01', hour: 0, value: 1234},
    ]);
  });
});

describe('fetchPredictionsCsv', () => {
  it('returns parsed array on 200', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response('route;date;hour;value\n1;2025-11-01;0;1188\n', {status: 200}),
      ),
    );
    const rows = await fetchPredictionsCsv();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({routeId: 1, date: '2025-11-01', hour: 0, value: 1188});
  });

  it('returns [] on 500', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(new Response('boom', {status: 500})),
    );
    expect(await fetchPredictionsCsv()).toEqual([]);
  });

  it('returns [] on network error', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('network')));
    expect(await fetchPredictionsCsv()).toEqual([]);
  });

  it('returns [] when CSV body is empty', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(new Response('', {status: 200})),
    );
    expect(await fetchPredictionsCsv()).toEqual([]);
  });

  it('returns [] when CSV body is header-only', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(new Response('route;date;hour;value\n', {status: 200})),
    );
    expect(await fetchPredictionsCsv()).toEqual([]);
  });
});

describe('fetchActualsCsv', () => {
  it('returns parsed array on 200', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(
          'route;date;hour;value\n1;2025-10-31;0;500\n',
          {status: 200},
        ),
      ),
    );
    const rows = await fetchActualsCsv();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({routeId: 1, date: '2025-10-31', hour: 0, value: 500});
  });

  it('returns [] on 500', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(new Response('boom', {status: 500})),
    );
    expect(await fetchActualsCsv()).toEqual([]);
  });
});
