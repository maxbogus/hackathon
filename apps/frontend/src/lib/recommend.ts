/**
 * T-130: «ехать сейчас или подождать» — pure function for the passenger-mode UI.
 *
 * Given a list of upcoming trams (sorted by ETA, ascending), produce an
 * action-oriented recommendation. The function is intentionally pure:
 *
 * - no React, no DOM — so it can be unit-tested (and reused server-side)
 * - no I/O, no datetime — so the same input always yields the same output
 *
 * The passenger-mode page (T-129) imports this and renders the returned
 * Recommendation via a coloured <Alert>. The Russian copy is hard-coded
 * on purpose — this MVP is targeted at a Moscow audience.
 *
 * Decision tree (see recommend.test.ts for the corresponding cases):
 *
 *   ┌─ input list empty                       ──► "no data" (info)
 *   ├─ closest tram already left (eta=0)      ──► fall back to next tram
 *   ├─ load < 70% on the closest tram          ──► "board — comfortable" (success)
 *   ├─ load >= 90% on the closest tram
 *   │     ├─ next tram ≤ 10 min away          ──► "wait N min — much lighter" (warning)
 *   │     └─ otherwise                        ──► "tight, no better option" (warning)
 *   └─ load in 70..90% (grey zone)
 *         ├─ next ≤ 8 min AND ≥ 15 pp emptier ─► "wait N min — lighter" (info)
 *         └─ otherwise                        ──► "board — load is acceptable" (success)
 */

export interface ETAPrediction {
  /** Tram route id (matches route_id from /api/v1/predictions/...). */
  route_id: number;
  /** Human-readable route label (e.g. "А", "39"). */
  route_name: string;
  /** Time until arrival in minutes. 0 means "left the stop moments ago". */
  eta_min: number;
  /** Predicted load as percentage of tram capacity (0..100). */
  predicted_load_pct: number;
  /** Id of the model that produced the prediction, for auditability. */
  model_id: string;
}

/** MUI-like severity levels — maps directly to <Alert severity=...>. */
export type Severity = 'success' | 'warning' | 'info';

export interface Recommendation {
  /** Russian user-facing sentence; safe to drop straight into the DOM. */
  text: string;
  /** A single emoji used as the icon in the alert. */
  emoji: string;
  /** Maps to <Alert severity={r.severity}>. */
  severity: Severity;
}

// Tunables — kept here so the rationale is searchable and editable in one place.
/** Below this load we consider the tram "comfortable". */
const LOAD_COMFORTABLE_MAX = 70;
/** At/above this load we tell the passenger to wait or warn about crowding. */
const LOAD_CROWDED_MIN = 90;
/** Within the grey zone, this is how far in the future the next tram must be. */
const GREY_ZONE_NEXT_ETA_MAX = 8;
/** In the grey zone, the next tram must be at least this many pp emptier. */
const GREY_ZONE_LOAD_DROP_MIN = 15;
/** When load >= 90%, this is how far in the future the next tram must be. */
const CROWDED_NEXT_ETA_MAX = 10;

// Emoji constants — kept once so the visual style is consistent.
const EMOJI_BOARD = '✅';
const EMOJI_WAIT = '⏳';
const EMOJI_CROWDED = '⚠️';
const EMOJI_NO_DATA = '❓';

/**
 * Convert a list of upcoming trams into a single human-readable recommendation.
 *
 * Behaviour is fully determined by the input — no clock, no randomness, no
 * network — so the function can be called inside a useMemo without having
 * to worry about referential stability beyond the inputs themselves.
 */
export function recommend(trams: readonly ETAPrediction[]): Recommendation {
  if (trams.length === 0) {
    return noData();
  }

  // After the length check the list is non-empty, so the index access is safe.
  // We still pick the first tram via .find() so we satisfy noUncheckedIndexedAccess
  // and no-non-null-assertion without sprinkling `!` operators through the code.
  const first = trams[0];
  if (first === undefined) {
    // Defensive — unreachable under TS narrowing, but keeps the function total.
    return noData();
  }

  // Pick the first tram that hasn't already left (eta > 0). If all trams in
  // the list report eta == 0 we fall back to the first one — better than
  // returning "no data" when the backend clearly returned *something*.
  const current = trams.find((t) => t.eta_min > 0) ?? first;
  const next = trams.find((t) => t.eta_min > current.eta_min);

  if (current.predicted_load_pct < LOAD_COMFORTABLE_MAX) {
    return boardComfortably();
  }

  if (current.predicted_load_pct >= LOAD_CROWDED_MIN) {
    return crowded(next);
  }

  // Grey zone 70..90%.
  return greyZone(current, next);
}

// Private helpers — each returns a complete Recommendation, never partial fields.

function noData(): Recommendation {
  return { text: 'Нет данных о ближайших рейсах', emoji: EMOJI_NO_DATA, severity: 'info' };
}

function boardComfortably(): Recommendation {
  return { text: 'Садитесь — будет комфортно', emoji: EMOJI_BOARD, severity: 'success' };
}

function crowded(next: ETAPrediction | undefined): Recommendation {
  if (next && next.eta_min <= CROWDED_NEXT_ETA_MAX) {
    return {
      text: `Подождите ${next.eta_min} мин — будет значительно свободнее`,
      emoji: EMOJI_CROWDED,
      severity: 'warning',
    };
  }
  return {
    text: 'Будет тесно — но других вариантов нет',
    emoji: EMOJI_CROWDED,
    severity: 'warning',
  };
}

function greyZone(
  current: ETAPrediction,
  next: ETAPrediction | undefined,
): Recommendation {
  const nextIsWorthWaiting =
    next !== undefined &&
    next.eta_min <= GREY_ZONE_NEXT_ETA_MAX &&
    current.predicted_load_pct - next.predicted_load_pct >= GREY_ZONE_LOAD_DROP_MIN;

  if (nextIsWorthWaiting && next) {
    return {
      text: `Подождите ${next.eta_min} мин — будет свободнее`,
      emoji: EMOJI_WAIT,
      severity: 'info',
    };
  }
  return {
    text: 'Садитесь — загрузка приемлемая',
    emoji: EMOJI_BOARD,
    severity: 'success',
  };
}
