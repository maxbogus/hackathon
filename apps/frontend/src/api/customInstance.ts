/**
 * Orval mutator — обёртка над fetch, чтобы все сгенерированные хуки
 * использовали единый HTTP-клиент (с Vite proxy, CORS, error handling).
 *
 * Конвенция: T-127 нужен только endpoint /api/v1/predictions/eta, поэтому
 * mutator пробрасывает `signal` для AbortController (TanStack Query
 * использует его для отмены запросов).
 *
 * Этот файл — ручной код (НЕ generated). Если OpenAPI добавляет новый
 * endpoint — перегенерируйте через `make fe-gen`.
 */

export interface CustomRequestInit extends Omit<RequestInit, 'body'> {
  url: string;
  /** Query-string params — orval передаёт их отдельным полем, не через URL. */
  params?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
}

export const customInstance = async <T>(config: CustomRequestInit): Promise<T> => {
  const { url, method = 'GET', params, body, headers, ...rest } = config;

  // Append query string if params provided.
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

  const response = await fetch(fullUrl, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...rest,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText} (${fullUrl})`);
  }

  // 204 No Content → пустой ответ
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
};

export default customInstance;
