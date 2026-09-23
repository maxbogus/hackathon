/**
 * T-141: Recursive `TKey` type — turn the nested `TEXTS` shape into a flat
 * union of dot-paths (e.g. "dispatcher.alerts.card.severityCritical").
 *
 * Why this matters:
 *   - `t(key)` only accepts valid keys at compile time.
 *   - An invalid literal like `t("dispatcher.alerts.cards.foo")` is a hard
 *     type error -- developers don't ship typos to runtime.
 *   - Renaming a string in `ru-RU.ts` propagates a type error everywhere
 *     it's referenced, so call sites stay in sync.
 *
 * The implementation is the standard `Leaves<T>` recursion template:
 *   - If a node is a string, we expose its own key as a valid path.
 *   - If a node is a nested object, we recurse into it and join with ".".
 *   - Function-valued leaves (used by `tf()` for interpolation) are also
 *     exposed -- they're "leaves" by the same logic.
 *
 * Adapted from https://twitter.com/matt Pocock  -- standard TS pattern.
 */

import type { TEXTS } from "./ru-RU";

type Join<K extends string, P extends string> = `${K}.${P}`;

type Leaves<T> = T extends object
  ? {
      [K in keyof T & string]: T[K] extends string | ((...args: never[]) => string)
        ? K
        : T[K] extends readonly unknown[]
          ? K
          : Join<K, Leaves<T[K]>>;
    }[keyof T & string]
  : never;

/**
 * Compile-time-enforced dot-path into `TEXTS`. Adding a leaf to `ru-RU.ts`
 * immediately grants the corresponding `TKey` literal here.
 */
export type TKey = Leaves<typeof TEXTS>;
