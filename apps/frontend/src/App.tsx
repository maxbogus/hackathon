/**
 * App shell with a role-switcher in the header.
 *
 * T-129: the most important role for the hackathon demo is the *passenger* —
 * they are the primary beneficiary ("когда приедет и будет ли место?"). The
 * switcher in the header lets the dispatcher switch between the four
 * personas defined in the AGENTS.md / hackathon brief:
 *
 *   🧍 Пассажир  → <PassengerMode>
 *   🎛️ Диспетчер → placeholder (T-131 will build alerts)
 *   📊 Аналитик  → placeholder
 *   🔮 Планировщик → placeholder
 *
 * Routing is intentionally trivial (useState) until TanStack Router file-
 * based routes land (F-009 + T-129 follow-up). At that point we'll convert
 * the four buttons into <Link>s and lift the role into the URL.
 */

import { useState } from 'react';

import { PassengerMode } from '@/pages/PassengerMode';

type Role = 'passenger' | 'dispatcher' | 'analyst' | 'planner';

interface RoleDef {
  id: Role;
  emoji: string;
  label: string;
  description: string;
}

const ROLES: ReadonlyArray<RoleDef> = [
  {
    id: 'passenger',
    emoji: '🧍',
    label: 'Пассажир',
    description: 'Когда приедет трамвай и будет ли место?',
  },
  {
    id: 'dispatcher',
    emoji: '🎛️',
    label: 'Диспетчер',
    description: 'Алерты по перегрузу (T-131)',
  },
  {
    id: 'analyst',
    emoji: '📊',
    label: 'Аналитик',
    description: 'Графики и метрики (T-035/037)',
  },
  {
    id: 'planner',
    emoji: '🔮',
    label: 'Планировщик',
    description: 'Monte Carlo сценарии (T-036)',
  },
];

function PlaceholderPanel({ role }: { role: RoleDef }): JSX.Element {
  return (
    <section style={{ padding: '16px 24px' }}>
      <h2 style={{ marginTop: 0 }}>
        {role.emoji} {role.label}
      </h2>
      <p style={{ color: '#666' }}>{role.description}</p>
      <p style={{ color: '#999', fontSize: 13 }}>
        Этот режим появится в следующих тикетах. Сейчас готов только режим «Пассажир».
      </p>
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
        <h1 style={{ margin: 0, fontSize: 20 }}>Transit-AI</h1>
        <p style={{ margin: '4px 0 12px', color: '#cbd5e1', fontSize: 13 }}>
          Хакатон: прогноз загрузки трамваев Москвы
        </p>

        <nav aria-label="Переключатель ролей" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
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
                {r.emoji} {r.label}
              </button>
            );
          })}
        </nav>
      </header>

      <main>
        {active.id === 'passenger' ? <PassengerMode /> : <PlaceholderPanel role={active} />}
      </main>
    </div>
  );
}
