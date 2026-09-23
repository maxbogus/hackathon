/**
 * T-135: Header navigation — 4 role links that activate the corresponding
 * TanStack Router route via URL.
 *
 * Rendered by the root layout (`__root.tsx`). The `activeRole` is computed
 * from `useRouterState().location.pathname` so the header always reflects
 * the current URL — deep linking, browser back/forward and reload all
 * just work because the URL *is* the state.
 *
 * a11y:
 *   - The container is a <nav> with an aria-label (the label comes from
 *     `app.navAriaLabel`).
 *   - Each entry is an <a> (TanStack Router's <Link> renders an <a>).
 *     `aria-pressed` is used so screen readers announce the active role
 *     the same way the old <button> switcher did.
 */

import { Link } from '@tanstack/react-router';
import type { ReactElement } from 'react';

import { t } from '@/lib/i18n/t';
import { ROLES, type RoleId } from '@/lib/roles';

export interface RoleSwitcherNavProps {
  /** Active role id, derived from the current URL by the caller. */
  readonly activeRole: RoleId;
}

export function RoleSwitcherNav({ activeRole }: RoleSwitcherNavProps): ReactElement {
  return (
    <nav aria-label={t('app.navAriaLabel')} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {ROLES.map((r) => {
        const isActive = r.id === activeRole;
        return (
          <Link
            key={r.id}
            to={`/${r.id}`}
            aria-pressed={isActive}
            data-active={isActive}
            style={{
              padding: '6px 12px',
              border: '1px solid #475569',
              borderRadius: 4,
              background: isActive ? '#3b82f6' : 'transparent',
              color: isActive ? '#fff' : '#cbd5e1',
              textDecoration: 'none',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: isActive ? 600 : 400,
            }}
          >
            {r.emoji} {t(r.labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}
