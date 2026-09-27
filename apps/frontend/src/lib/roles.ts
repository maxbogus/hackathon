/**
 * T-135 / T-200: Pure data for the three role personas.
 *
 * Extracted from App.tsx so that the file-based route components
 * (passenger.tsx, dispatcher.tsx, analyst.tsx) and the RoleSwitcherNav in
 * the root layout can both reference the same dispatch table without
 * re-implementing it.
 *
 * T-200 / D-027: the `planner` role was removed (was a placeholder tab
 * with no real dashboard). Only the three roles with working dashboards
 * remain. When Monte Carlo scenarios (T-036) land, this entry returns.
 *
 * Why a separate module (and no JSX here):
 *   - Pure data, no React, no router — easy to unit-test.
 *   - Adding a new role = adding one entry here + one trio of TKeys to
 *     `lib/i18n/ru-RU.ts` (T-141). TypeScript flags any mismatch.
 *   - The route files import the role they need, so they stay tiny.
 *   - JSX would force this file to be `.tsx`, but `.ts` is the right
 *     shape for "pure dispatch table" — clearer at a glance.
 *
 * The `placeholderKey` is intentionally shared (`app.rolePassenger.placeholder`
 * in ru-RU.ts) — kept for parity with future roles that may need a
 * "coming soon" copy.
 */

export type RoleId = 'passenger' | 'dispatcher' | 'analyst';

export interface RoleDef {
  /** URL slug, used as the route path. */
  readonly id: RoleId;
  /** Emoji rendered next to the role label in the header. */
  readonly emoji: string;
  /** TKey whose value is the role button label. */
  readonly labelKey:
    | 'app.rolePassenger.label'
    | 'app.roleDispatcher.label'
    | 'app.roleAnalyst.label';
  /** TKey whose value is the description shown in the placeholder panel. */
  readonly descriptionKey:
    | 'app.rolePassenger.description'
    | 'app.roleDispatcher.description'
    | 'app.roleAnalyst.description';
  /** Shared "coming soon" body. See file header for rationale. */
  readonly placeholderKey: 'app.rolePassenger.placeholder';
}

export const ROLES: ReadonlyArray<RoleDef> = [
  {
    id: 'passenger',
    emoji: '🧍',
    labelKey: 'app.rolePassenger.label',
    descriptionKey: 'app.rolePassenger.description',
    placeholderKey: 'app.rolePassenger.placeholder',
  },
  {
    id: 'dispatcher',
    emoji: '🎛️',
    labelKey: 'app.roleDispatcher.label',
    descriptionKey: 'app.roleDispatcher.description',
    placeholderKey: 'app.rolePassenger.placeholder',
  },
  {
    id: 'analyst',
    emoji: '📊',
    labelKey: 'app.roleAnalyst.label',
    descriptionKey: 'app.roleAnalyst.description',
    placeholderKey: 'app.rolePassenger.placeholder',
  },
];

/** Lookup helper for the active role from a URL pathname. */
export function roleFromPathname(pathname: string): RoleDef {
  const segment = pathname.split('/').filter(Boolean)[0];
  const found = ROLES.find((r) => r.id === segment);
  // ROLES always has a passenger entry — guaranteed by the literal above.
  // TS doesn't see through `noUncheckedIndexedAccess`, so we narrow here.
  const first: RoleDef | undefined = ROLES[0];
  if (!first) {
    throw new Error('lib/roles.ts: ROLES is empty — invariant broken');
  }
  return found ?? first;
}
