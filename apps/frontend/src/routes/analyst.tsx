/**
 * T-196 / T-200: "/analyst" → <AnalystDashboard /> с историей, прогнозами и фильтрами.
 *
 * Заменяет T-135 PlaceholderPanel. После T-200 этот маршрут — единственная
 * не-pseudo-role вкладка после passenger + dispatcher (planner удалён).
 */

import { createFileRoute } from '@tanstack/react-router';

import { AnalystDashboard } from '@/components/Charts/AnalystDashboard';

function AnalystRoute(): JSX.Element {
  return <AnalystDashboard />;
}

export const Route = createFileRoute('/analyst')({
  component: AnalystRoute,
});
