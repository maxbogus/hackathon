/**
 * T-135: TanStack Router — header role-switcher is rendered by the root
 * route and each role link activates the corresponding page via URL.
 *
 * What we assert:
 *   1. The header shows 4 <Link>s pointing to /passenger, /dispatcher,
 *      /analyst, /planner.
 *   2. The currently active link carries aria-pressed="true".
 *   3. The <Outlet /> renders the component for the active route
 *      (PassengerMode, AlertsPanel, PlaceholderPanel).
 *
 * Why MemoryHistory: tests need a deterministic URL that doesn't depend on
 * jsdom's window.location (which jsdom sets to "about:blank" by default).
 */

import { describe, expect, it } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router';

import { routeTree } from '../routeTree.gen';
import { RoleSwitcherNav } from '@/components/Layout/RoleSwitcherNav';

async function renderAt(pathname: string): Promise<void> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const history = createMemoryHistory({ initialEntries: [pathname] });
  const router = createRouter({
    routeTree,
    history,
    context: { queryClient },
  });
  // v1.x: navigation is asynchronous — load the initial route before
  // rendering so the outlet already has a match on the first paint.
  await router.load();
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

/**
 * Build a *minimal* router that contains a root route with our
 * <RoleSwitcherNav> inside. This keeps the unit tests for the nav free
 * of the full route tree — we only care that <Link>s render with the
 * right hrefs and aria-pressed flags.
 */
function renderNav(activeRole: 'passenger' | 'dispatcher' | 'analyst' | 'planner'): void {
  const RootRoute = createRootRoute({
    component: () => (
      <div>
        <RoleSwitcherNav activeRole={activeRole} />
        <main data-testid="nav-only" />
      </div>
    ),
  });
  const IndexRoute = createRoute({
    getParentRoute: () => RootRoute,
    path: '/',
    component: () => <div />,
  });
  const router = createRouter({
    routeTree: RootRoute.addChildren([IndexRoute]),
    history: createMemoryHistory({ initialEntries: ['/'] }),
  });
  render(<RouterProvider router={router} />);
}

describe('<RoleSwitcherNav>', () => {
  it('renders four role links pointing to /passenger, /dispatcher, /analyst, /planner', async () => {
    renderNav('passenger');
    const nav = await screen.findByLabelText(/переключатель ролей/i);
    const links = within(nav).getAllByRole('link');
    expect(links).toHaveLength(4);
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs).toEqual(
      expect.arrayContaining(['/passenger', '/dispatcher', '/analyst', '/planner']),
    );
  });

  it('marks the active role link with aria-pressed=true and others with aria-pressed=false', async () => {
    renderNav('dispatcher');
    const nav = await screen.findByLabelText(/переключатель ролей/i);
    const active = within(nav).getByRole('link', { name: /диспетчер/i });
    expect(active.getAttribute('aria-pressed')).toBe('true');
    const passenger = within(nav).getByRole('link', { name: /пассажир/i });
    expect(passenger.getAttribute('aria-pressed')).toBe('false');
  });
});

describe('router outlet', () => {
  it('renders the passenger panel at /passenger', async () => {
    await renderAt('/passenger');
    // PassengerMode renders an <h2> with "🧍 Пассажир — ближайшие трамваи"
    // (see lib/i18n/ru-RU.ts → passenger.modeTitle).
    expect(
      await screen.findByRole('heading', { name: /пассажир.*ближайшие трамваи/i }),
    ).toBeInTheDocument();
  });

  it('renders the dispatcher alerts panel at /dispatcher', async () => {
    await renderAt('/dispatcher');
    // AlertsPanel shows *something* (heading, loading, or error) the
    // moment the route mounts. The full data render needs MSW — not in
    // scope here (T-131-1 covered it).
    await waitFor(() => {
      const heading = screen.queryByRole('heading', { name: /диспетчер.*алерты/i });
      const loading = screen.queryByTestId('alerts-loading');
      const error = screen.queryByTestId('alerts-error');
      expect(heading ?? loading ?? error).toBeTruthy();
    });
  });

  it('renders the analyst placeholder at /analyst', async () => {
    await renderAt('/analyst');
    // PlaceholderPanel shows the role label as an <h2>.
    expect(await screen.findByRole('heading', { name: /аналитик/i })).toBeInTheDocument();
  });

  it('renders the planner placeholder at /planner', async () => {
    await renderAt('/planner');
    expect(await screen.findByRole('heading', { name: /планировщик/i })).toBeInTheDocument();
  });
});
