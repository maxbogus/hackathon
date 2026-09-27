/**
 * customInstance — orval mutator, единая HTTP-обёртка.
 *
 * Возвращает {data, status, headers} для доступа к response headers (T-196
 * нужно для X-Row-Count, X-CSV-MD5 из /predictions/export.csv).
 *
 * F-097: для совместимости с типизированными Orval хуками (data.alerts)
 * мутор возвращает **развёрнутый T** (а не {data, status, headers}), но
 * сохраняет helper getResponseHeaders() для случаев, когда нужны headers.
 *
 * Этот файл — ручной код (НЕ generated). Если OpenAPI добавляет новый
 * endpoint — перегенерируйте через `make fe-gen`.
 */

// Orval генерит URL уже с префиксом /api/v1/... (из OpenAPI paths в docs/api/openapi.json).
// Раньше тут было '/api' — это склеивалось с URL из Orval и давало /api/api/v1/... → 404 на nginx.
// VITE_API_URL остался для override в проде (например "https://api.example.com/api").
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

export interface CustomRequestInit extends Omit<RequestInit, 'body'> {
  url: string;
  /**
   * F-097: расширил тип с `string | number | boolean | undefined` до
   * `string | number | boolean | null | undefined`, чтобы Orval-generated
   * хуки с optional параметрами (например `from?: string | null`) могли
   * передавать null без TS-error. URLSearchParams ниже всё равно игнорирует
   * null (как undefined), что соответствует семантике «не отправлять».
   */
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  data?: unknown;  // orval генерит data: для POST/PUT bodies
  responseType?: 'json' | 'text';
}

/**
 * F-097 (T-216 + F-095 follow-up): response headers + status.
 * Раньше мутор возвращал `CustomResponse<T> = { data: T, ... }`,
 * но сгенерированные Orval хуки используют `T = Awaited<ReturnType<xxx>>`
 * и ожидают развёрнутый `T`, а не `CustomResponse<T>`. Это давало расхождения
 * в типах (data.alerts на CustomResponse<T>). Чтобы не менять 80+ хуков и
 * сохранить backward-compat, мутор теперь возвращает **T** + отдельный
 * объект-метаданные через lastHeaders/lastStatus (для случаев когда нужны headers).
 */
export interface ResponseEnvelope {
  headers: Record<string, string>;
  status: number;
  url: string;
}

/** Последний response envelope (singleton). Сбрасывается перед каждым fetch. */
let _lastEnvelope: ResponseEnvelope | null = null;

/** Получить headers/status последнего HTTP-ответа (для X-Row-Count, X-CSV-MD5). */
export function lastResponse(): ResponseEnvelope | null {
  return _lastEnvelope;
}

export const customInstance = async <T>(config: CustomRequestInit): Promise<T> => {
  const { url, method = 'GET', params, body, headers, responseType, ...rest } = config;

  let fullUrl = url;
  if (params) {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        qs.append(key, String(value));
      }
    }
    const queryString = qs.toString();
    if (queryString) {
      fullUrl = `${url}${url.includes('?') ? '&' : '?'}${queryString}`;
    }
  }

  const fullUrlWithBase = `${BASE_URL}${fullUrl}`;
  const response = await fetch(fullUrlWithBase, {
    method,
    headers: {
      Accept: responseType === 'text' ? 'text/csv' : 'application/json',
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...rest,
  });

  const responseHeaders: Record<string, string> = {};
  response.headers.forEach((value, key) => {
    responseHeaders[key] = value;
  });

  _lastEnvelope = { headers: responseHeaders, status: response.status, url: fullUrlWithBase };

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText} (${fullUrlWithBase})`);
  }

  let data: T;
  if (responseType === 'text') {
    data = (await response.text()) as unknown as T;
  } else if (response.status === 204) {
    data = undefined as T;
  } else {
    data = (await response.json()) as T;
  }

  return data;
};

export default customInstance;
