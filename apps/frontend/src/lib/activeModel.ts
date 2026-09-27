/**
 * T-201: active-model helper.
 *
 * Fetches /api/v1/models/active and returns the model's id + WAPE-score.
 * Used by the passenger-mode footer (T-201) to show "Model: baseline_v1
 * · WAPE-score 0.9272" instead of the previous hard-coded "—".
 *
 * Why a plain fetch (not TanStack Query):
 *   - Only one consumer (PassengerMode), polled once on mount.
 *   - Avoids threading QueryClientProvider through isolated unit tests.
 *   - Failure path is silent — UI keeps showing ETA cards.
 *
 * Why not orval's `useGetActiveModelApiV1ModelsActiveGet`:
 *   - That hook needs a QueryClientProvider, which is fine for production
 *     but adds friction to `PassengerMode.test.tsx`. The cost of adding
 *     QueryClientProvider there outweighs the win of declarative caching
 *     (we cache for 60s anyway via the App-level `staleTime`).
 */

export interface ActiveModelInfo {
  readonly model_id: string;
  readonly wape_score: number | null;
}

/**
 * Fetch the active model from the backend. Returns `null` on any failure
 * (network, 5xx, malformed JSON) — callers should treat that as
 * "footer has no extra info".
 *
 * The backend returns `wape_score` nested inside `metrics`:
 *   {
 *     "model_id": "baseline_v1",
 *     "metrics": { "wape_score": 0.9272, ... },
 *     ...
 *   }
 * We also accept a top-level `wape_score` for backward compatibility.
 */
export async function fetchActiveModel(
  signalOrBaseUrl?: AbortSignal | string,
  maybeSignal?: AbortSignal,
): Promise<ActiveModelInfo | null> {
  const baseUrl =
    typeof signalOrBaseUrl === 'string' ? signalOrBaseUrl : '/api/v1/models/active';
  const signal = typeof signalOrBaseUrl === 'object' ? signalOrBaseUrl : maybeSignal;
  try {
    const response = await fetch(baseUrl, {
      headers: { Accept: 'application/json' },
      ...(signal ? { signal } : {}),
    });
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as Record<string, unknown>;
    const modelId = typeof data['model_id'] === 'string' ? data['model_id'] : null;

    // WAPE-score: prefer nested metrics.wape_score, fall back to top-level.
    const metrics = (data['metrics'] ?? {}) as Record<string, unknown>;
    const wapeRaw = metrics['wape_score'] ?? data['wape_score'];
    const wape =
      typeof wapeRaw === 'number'
        ? wapeRaw
        : typeof wapeRaw === 'string'
          ? Number.parseFloat(wapeRaw)
          : null;

    if (!modelId) {
      return null;
    }
    return { model_id: modelId, wape_score: Number.isFinite(wape) ? wape : null };
  } catch {
    return null;
  }
}

/**
 * Format WAPE-score as a 4-decimal Russian string, or `null` if absent.
 * Used by `tf('passenger.activeModelFooter', modelId, wape)`.
 */
export function formatWapeScore(wape: number | null): string | null {
  if (wape === null || !Number.isFinite(wape)) {
    return null;
  }
  return wape.toFixed(4);
}
