/**
 * TanStack Router file-based routing — root route.
 *
 * T-135: this is now the app shell.
 *   - Header (title + tagline + role-switcher with 4 URL <Link>s).
 *   - <Outlet /> renders the matched child route (passenger, dispatcher,
 *     analyst, planner). The role lives in the URL — browser back/forward
 *     and reload all work for free.
 *
 * Required by @tanstack/router-vite-plugin (F-009): the plugin refuses
 * to start without this file even if all routes live elsewhere.
 *
 * Why the active role is computed from the URL (not React state):
 *   The URL is the source of truth. `useRouterState` reads it on every
 *   render, so a deep link to /dispatcher paints the dispatcher tab as
 *   active without any state plumbing.
 */

import { Outlet, createRootRoute, useRouterState } from '@tanstack/react-router';

import { RoleSwitcherNav } from '@/components/Layout/RoleSwitcherNav';
import { t } from '@/lib/i18n/t';
import { roleFromPathname } from '@/lib/roles';

export const Route = createRootRoute({
  component: RootShell,
});

function RootShell(): JSX.Element {
  const pathname = useRouterState({
    select: (s) => s.location.pathname,
  });
  const activeRole = roleFromPathname(pathname);

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
        <p style={{ margin: '4px 0 12px', color: '#cbd5e1', fontSize: 13 }}>{t('app.tagline')}</p>
        <RoleSwitcherNav activeRole={activeRole.id} />
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
}
