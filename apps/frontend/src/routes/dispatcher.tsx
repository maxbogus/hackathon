/**
 * T-135: "/dispatcher" → <AlertsPanel />.
 *
 * T-131: replaces the old PlaceholderPanel for the dispatcher role.
 * TanStack Query's `refetchInterval` does the polling (D-013).
 */

import { createFileRoute } from '@tanstack/react-router';

import { AlertsPanel } from '@/components/Dispatcher/AlertsPanel';

export const Route = createFileRoute('/dispatcher')({
  component: AlertsPanel,
});
