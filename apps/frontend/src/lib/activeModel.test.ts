/**
 * T-201: activeModel helper.
 *
 * Covers the two failure modes (network, non-2xx, malformed JSON) plus
 * the happy path. The WAPE-score formatter is exercised in isolation.
 */

import { describe, expect, it, vi, afterEach } from 'vitest';

import { fetchActiveModel, formatWapeScore } from './activeModel';

describe('fetchActiveModel', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns {model_id, wape_score} on a 200 with valid JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ model_id: 'baseline_v1', wape_score: 0.9272 }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );

    const result = await fetchActiveModel();
    expect(result).toEqual({ model_id: 'baseline_v1', wape_score: 0.9272 });
  });

  it('returns null on a 5xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('boom', { status: 503 })),
    );

    const result = await fetchActiveModel();
    expect(result).toBeNull();
  });

  it('returns null when fetch throws (network down)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('network down');
      }),
    );

    const result = await fetchActiveModel();
    expect(result).toBeNull();
  });

  it('returns null on a 200 with no model_id field', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({}), { status: 200 })),
    );

    const result = await fetchActiveModel();
    expect(result).toBeNull();
  });

  it('accepts a wape_score that comes back as a string ("0.9272")', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ model_id: 'x', wape_score: '0.9272' }), {
          status: 200,
        }),
      ),
    );

    const result = await fetchActiveModel();
    expect(result).toEqual({ model_id: 'x', wape_score: 0.9272 });
  });
});

describe('formatWapeScore', () => {
  it('formats a normal positive score to 4 decimals', () => {
    expect(formatWapeScore(0.9272)).toBe('0.9272');
    expect(formatWapeScore(0.8751)).toBe('0.8751');
  });

  it('returns null for null', () => {
    expect(formatWapeScore(null)).toBeNull();
  });

  it('returns null for NaN', () => {
    expect(formatWapeScore(Number.NaN)).toBeNull();
  });
});
