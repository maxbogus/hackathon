/**
 * T-135 / T-200: "/dispatcher" → <AlertsPanel />.
 *
 * T-131: replaces the old PlaceholderPanel for the dispatcher role.
 * TanStack Query's `refetchInterval` does the polling (D-013).
 *
 * T-225 / D-037: этот route остаётся как ORPHAN — больше НЕ в nav
 * (см. lib/roles.ts: dispatcher удалён из ROLES). Прямой URL /dispatcher
 * продолжает работать (рендерит AlertsPanel) для дебага и обратной
 * совместимости. Если в будущем понадобится вернуть вкладку — добавить
 * запись в ROLES + ссылку автоматически появится в RoleSwitcherNav.
 */

import { createFileRoute } from '@tanstack/react-router';

import { AlertsPanel } from '@/components/Dispatcher/AlertsPanel';

export const Route = createFileRoute('/dispatcher')({
  component: AlertsPanel,
});
