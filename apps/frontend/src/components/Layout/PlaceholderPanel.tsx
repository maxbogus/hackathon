/**
 * T-135: Placeholder panel for roles whose real dashboard is not built
 * yet (analyst, planner).
 *
 * Pure presentation: receives a RoleDef and renders label + description +
 * "coming soon" copy. The "coming soon" copy is shared across all roles
 * (see RoleDef.placeholderKey) — see lib/roles.ts for rationale.
 *
 * Why a separate component:
 *   - Routes `analyst.tsx` and `planner.tsx` stay thin (3-line wrappers).
 *   - Easy to unit-test in isolation (no router context needed).
 */

import type { ReactElement } from 'react';

import { t } from '@/lib/i18n/t';
import type { RoleDef } from '@/lib/roles';

export function PlaceholderPanel({ role }: { role: RoleDef }): ReactElement {
  return (
    <section style={{ padding: '16px 24px' }}>
      <h2 style={{ marginTop: 0 }}>
        {role.emoji} {t(role.labelKey)}
      </h2>
      <p style={{ color: '#666' }}>{t(role.descriptionKey)}</p>
      <p style={{ color: '#999', fontSize: 13 }}>{t(role.placeholderKey)}</p>
    </section>
  );
}
