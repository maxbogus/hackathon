/**
 * customInstance — orval mutator, единая HTTP-обёртка.
 *
 * Возвращает {data, status, headers} для доступа к response headers (T-196
 * нужно для X-Row-Count, X-CSV-MD5 из /predictions/export.csv).
 *
 * Этот файл — ручной код (НЕ generated). Если OpenAPI добавляет новый
 * endpoint — перегенерируйте через `make fe-gen`.
 */

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api';

export interface CustomRequestInit extends Omit<RequestInit, 'body'> {
  url: string;
  params?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  responseType?: 'json' | 'text';
}

export interface CustomResponse<T> {
  data: T;
  status: number;
  headers: Record<string, string>;
}

export const customInstance = async <T>(config: CustomRequestInit): Promise<CustomResponse<T>> => {
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

  const response = await fetch(`${BASE_URL}${fullUrl}`, {
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

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText} (${fullUrl})`);
  }

  let data: T;
  if (responseType === 'text') {
    data = (await response.text()) as unknown as T;
  } else if (response.status === 204) {
    data = undefined as T;
  } else {
    data = (await response.json()) as T;
  }

  return { data, status: response.status, headers: responseHeaders };
};

export default customInstance;
