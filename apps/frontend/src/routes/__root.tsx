/**
 * TanStack Router file-based routing — root route.
 *
 * Required by @tanstack/router-vite-plugin (F-009). Even though we don't use
 * file-based routing yet (App.tsx currently uses local useState), the plugin
 * scans this directory at config-resolution time and refuses to start if
 * `__root.tsx` is missing.
 *
 * When T-129-follow-up (or any ticket that introduces real routing) lands,
 * this file will be expanded to a proper <Outlet /> + <TanStackRouterProvider>.
 * For now it stays minimal so `yarn dev` and `yarn build` succeed.
 */

import { Outlet, createRootRoute } from '@tanstack/react-router';

export const Route = createRootRoute({
  component: Outlet,
});
