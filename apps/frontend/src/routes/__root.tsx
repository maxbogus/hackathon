/**
 * TanStack Router file-based routing - root route.
 *
 * T-135: this is now the app shell.
 *   - Header (title + tagline + role-switcher with 2 URL <Link>s — Диспетчер
 *     + Аналитик, см. T-225 / D-037).
 *   - <Outlet /> renders the matched child route (passenger = Диспетчер,
 *     analyst). The /dispatcher route still exists as an orphan (AlertsPanel)
 *     for backward compatibility — it is reachable by direct URL but no
 *     longer surfaced in the role-switcher. The role lives in the URL —
 *     browser back/forward and reload all work for free.
 *
 * Required by @tanstack/router-vite-plugin (F-009): the plugin refuses
 * to start without this file even if all routes live elsewhere.
 *
 * Why the active role is computed from the URL (not React state):
 *   The URL is the source of truth. `useRouterState` reads it on every
 *   render, so a deep link to /passenger paints the Диспетчер tab as
 *   active without any state plumbing.
 *
 * QueryClientProvider (T-AUDIT-FIX): TanStack Query hooks (useQuery in
 * AnalystDashboard, AlertsPanel, FiltersPanel, HistoricalChart, etc.)
 * throw "No QueryClient set" without this. useState factory keeps it
 * StrictMode-safe (fresh client on every dev double-render).
 */

import { useState } from 'react';
import { Outlet, createRootRoute, useRouterState } from '@tanstack/react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { RoleSwitcherNav } from '@/components/Layout/RoleSwitcherNav';
import { t } from '@/lib/i18n/t';
import { roleFromPathname } from '@/lib/roles';

export const Route = createRootRoute({
  component: RootShell,
});

function RootShell(): JSX.Element {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 30_000,
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={queryClient}>
      <RootShellInner />
    </QueryClientProvider>
  );
}

function RootShellInner(): JSX.Element {
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
