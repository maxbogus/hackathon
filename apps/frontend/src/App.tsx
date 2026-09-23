/**
 * App shell with a role-switcher in the header.
 *
 * T-129: the most important role for the hackathon demo is the *passenger* —
 * they are the primary beneficiary ("когда приедет и будет ли место?"). The
 * switcher in the header lets the dispatcher switch between the four
 * personas defined in AGENTS.md / hackathon brief:
 *
 *   🧍 Пассажир  → <PassengerMode>
 *   🎛️ Диспетчер → <AlertsPanel>  (T-131)
 *   📊 Аналитик  → placeholder
 *   🔮 Планировщик → placeholder
 *
 * Routing is intentionally trivial (useState) until TanStack Router file-
 * based routes land (T-135). At that point we convert the four buttons
 * into <Link>s and lift the role into the URL.
 *
 * T-141: every user-facing string now flows through `t()` from
 * `lib/i18n`, not JSX literals. The dispatch table maps `Role.id` to the
 * corresponding `TKey` triple, keeping this file free of raw Russian copy.
 */

import { useState } from 'react';

import { t } from '@/lib/i18n/t';

import { PassengerMode } from '@/pages/PassengerMode';
import { AlertsPanel } from '@/components/Dispatcher/AlertsPanel';

type Role = 'passenger' | 'dispatcher' | 'analyst' | 'planner';

interface RoleDef {
  id: Role;
  emoji: string;
  /** TKey whose value is the role button label (any of the four). */
  labelKey: 'app.rolePassenger.label' | 'app.roleDispatcher.label' | 'app.roleAnalyst.label' | 'app.rolePlanner.label';
  /** TKey whose value is the description shown in the placeholder panel. */
  descriptionKey:
    | 'app.rolePassenger.description'
    | 'app.roleDispatcher.description'
    | 'app.roleAnalyst.description'
    | 'app.rolePlanner.description';
  /** TKey whose value is the "coming soon" body. Shared across roles. */
  placeholderKey: 'app.rolePassenger.placeholder';
}

/**
 * Static role table — pure data, no React. Labels and descriptions live in
 * `lib/i18n`; adding a new role means: (a) add the role here, (b) add the
 * three TKeys to `lib/i18n/ru-RU.ts`. TypeScript will flag any mismatch.
 */
const ROLES: ReadonlyArray<RoleDef> = [
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
  {
    id: 'planner',
    emoji: '🔮',
    labelKey: 'app.rolePlanner.label',
    descriptionKey: 'app.rolePlanner.description',
    placeholderKey: 'app.rolePassenger.placeholder',
  },
];

function PlaceholderPanel({ role }: { role: RoleDef }): JSX.Element {
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

export function App(): JSX.Element {
  const [role, setRole] = useState<Role>('passenger');
  const found: RoleDef | undefined = ROLES.find((r) => r.id === role);
  const firstRole: RoleDef | undefined = ROLES[0];
  if (!found || !firstRole) {
    throw new Error('ROLES array must not be empty');
  }
  const active: RoleDef = found ?? firstRole;

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      <header
        style={{
          padding: '16px 24px',
          background: '#1f2937',
          color: '#fff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20 }}>{t('app.title')}</h1>
        <p style={{ margin: '4px 0 12px', color: '#cbd5e1', fontSize: 13 }}>
          {t('app.tagline')}
        </p>

        <nav
          aria-label={t('app.navAriaLabel')}
          style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}
        >
          {ROLES.map((r) => {
            const isActive = r.id === role;
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => setRole(r.id)}
                aria-pressed={isActive}
                data-active={isActive}
                style={{
                  padding: '6px 12px',
                  border: '1px solid #475569',
                  borderRadius: 4,
                  background: isActive ? '#3b82f6' : 'transparent',
                  color: isActive ? '#fff' : '#cbd5e1',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {r.emoji} {t(r.labelKey)}
              </button>
            );
          })}
        </nav>
      </header>

      <main>
        {active.id === 'passenger' ? (
          <PassengerMode />
        ) : active.id === 'dispatcher' ? (
          <AlertsPanel />
        ) : (
          <PlaceholderPanel role={active} />
        )}
      </main>
    </div>
  );
}
