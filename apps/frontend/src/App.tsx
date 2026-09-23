/**
 * App shell — mounts the TanStack Router instance and hands the tree over
 * to <RouterProvider>.
 *
 * T-135: routing now lives in `routes/`. The role-switcher, header layout
 * and <Outlet/> all live in `routes/__root.tsx` (the root layout). This
 * file only owns the router instance — created once per module load, reused
 * across renders. StrictMode-safe because the router is module-level.
 *
 * T-141: every user-facing string still flows through `t()`. Routing
 * doesn't add any new UI strings; the existing `lib/i18n` keys carry over.
 */

import { RouterProvider, createRouter } from '@tanstack/react-router';

import { routeTree } from './routeTree.gen';

/**
 * Module-level singleton: one router instance per browser tab. Creating
 * it on every render would reset the navigation stack and break the URL.
 *
 * `defaultPreload: 'intent'` pre-fetches the next route's data when the
 * user hovers a <Link> — a nice demo touch for the jury without any
 * explicit prefetch wiring.
 */
const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
});

/**
 * Register the router type so <Link>, useRouterState and friends get full
 * type-safe route inference (`to: '/dispatcher'` is checked against the
 * actual route tree, not `string`).
 */
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

export function App(): JSX.Element {
  return <RouterProvider router={router} />;
}
