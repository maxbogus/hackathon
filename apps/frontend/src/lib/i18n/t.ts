/**
 * T-141: runtime lookup for the hybrid text registry.
 *
 * Two functions:
 *   - `t(key)` — pure lookup; returns a static string for leaf keys.
 *   - `tf(key, ...args)` — for parameterised strings (e.g. `tf("passenger.etaCard.etaTemplate", 5)`).
 *
 * After the hackathon, swap this implementation for `react-i18next`; the
 * signature stays the same and no call site changes.
 */

import { TEXTS } from './ru-RU';
import type { TKey } from './keys';

/**
 * Look up a static string by `TKey`. The dot-path is split on "." and walked
 * through `TEXTS`; the last segment must resolve to a string literal.
 *
 * Implementation notes:
 *   - The `as any` on the indexer is unavoidable: TS can't model "the leaf is a
 *     string" through arbitrary depth of nested object types without
 *     complicating `Leaves<>`. The `as string` cast at the end is safe because
 *     `TKey` constrains the path to leaves.
 *   - No caching needed: a single lookup is ~5 property reads, called
 *     synchronously from JSX, and the dictionary has fewer than 30 keys.
 */
export function t(key: TKey): string {
  const segments = key.split('.');
  let cur: unknown = TEXTS;
  for (const s of segments) {
    if (cur !== null && typeof cur === 'object') {
      cur = (cur as Record<string, unknown>)[s];
    } else {
      throw new Error(`t(): cannot descend into ${key} at segment "${s}"`);
    }
  }
  if (typeof cur !== 'string') {
    throw new Error(`t(): leaf for ${key} is not a string (got ${typeof cur})`);
  }
  return cur;
}

/**
 * Look up a function-valued string and call it with `args`.
 *
 * The same lookup strategy as `t()` -- the only difference is that the leaf
 * is expected to be a function rather than a string. We use the same
 * `TKey`, which works because `Leaves<T>` exposes function-valued leaves too.
 */
export function tf(key: TKey, ...args: readonly unknown[]): string {
  const segments = key.split('.');
  let cur: unknown = TEXTS;
  for (const s of segments) {
    if (cur !== null && typeof cur === 'object') {
      cur = (cur as Record<string, unknown>)[s];
    } else {
      throw new Error(`tf(): cannot descend into ${key} at segment "${s}"`);
    }
  }
  if (typeof cur !== 'function') {
    throw new Error(`tf(): leaf for ${key} is not a function (got ${typeof cur})`);
  }
  return (cur as (...a: readonly unknown[]) => string)(...args);
}
