/**
 * Регрессионные тесты для customInstance.
 *
 * F-NNN: защита от двойного /api/api в URL.
 * Если кто-то снова задаст BASE_URL='/api' (или любой префикс, конфликтующий с путями
 * OpenAPI), эти тесты упадут.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { customInstance } from './customInstance';

describe('customInstance URL composition', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(
      new Response('{}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('не склеивает лишний /api с URL из Orval (F-NNN regression)', async () => {
    await customInstance({ url: '/api/v1/insights/alerts', method: 'GET' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calledUrl = fetchMock.mock.calls[0]?.[0] as string;

    // КРИТИЧНО: ровно один /api, не /api/api
    expect(calledUrl).toBe('/api/v1/insights/alerts');
    expect(calledUrl).not.toContain('/api/api');
    expect(calledUrl.startsWith('/api/')).toBe(true);
  });

  it('сохраняет query-параметры из Orval params', async () => {
    await customInstance({
      url: '/api/v1/historical/7',
      method: 'GET',
      params: {
        from: '2025-09-01',
        to: '2025-10-31',
        granularity: 'day',
      },
    });

    const calledUrl = fetchMock.mock.calls[0]?.[0] as string;
    expect(calledUrl.startsWith('/api/v1/historical/7?')).toBe(true);
    expect(calledUrl).toContain('from=2025-09-01');
    expect(calledUrl).toContain('to=2025-10-31');
    expect(calledUrl).toContain('granularity=day');
    expect(calledUrl).not.toContain('/api/api');
  });

  it('бросает Error со статус-кодом и URL при HTTP 404', async () => {
    vi.unstubAllGlobals();
    vi.stubGlobal('fetch', () =>
      Promise.resolve(
        new Response('Not Found', { status: 404, statusText: 'Not Found' }),
      ),
    );

    await expect(
      customInstance({ url: '/api/v1/predictions/db/7', method: 'GET' }),
    ).rejects.toThrow(/HTTP 404.*\/api\/v1\/predictions\/db\/7/);
  });
});
