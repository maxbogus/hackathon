/**
 * T-196: "/analyst" → <AnalystDashboard /> с историей, прогнозами и фильтрами.
 *
 * Заменяет T-135 PlaceholderPanel.
 */

import { createFileRoute } from '@tanstack/react-router';

import { AnalystDashboard } from '@/components/Charts/AnalystDashboard';

function AnalystRoute(): JSX.Element {
  return <AnalystDashboard />;
}

export const Route = createFileRoute('/analyst')({
  component: AnalystRoute,
});
