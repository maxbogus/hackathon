/**
 * T-135: "/planner" → <PlaceholderPanel role="planner" />.
 *
 * Planner dashboards (Monte Carlo scenarios, T-036) will land later.
 * See lib/i18n/ru-RU.ts.
 */

import { createFileRoute } from '@tanstack/react-router';

import { PlaceholderPanel } from '@/components/Layout/PlaceholderPanel';
import { ROLES, type RoleDef } from '@/lib/roles';

const PLANNER_ROLE: RoleDef | undefined = ROLES.find((r) => r.id === 'planner');
if (!PLANNER_ROLE) {
  throw new Error('lib/roles.ts: planner role is missing — invariant broken');
}

function PlannerRoute(): JSX.Element {
  // After the throw above, TS still widens the type to `RoleDef | undefined`
  // because ROLES.find returns `RoleDef | undefined`. The narrowing happens
  // in the if-block but not across function boundaries, so we re-narrow here.
  if (!PLANNER_ROLE) {
    throw new Error('unreachable');
  }
  return <PlaceholderPanel role={PLANNER_ROLE} />;
}

export const Route = createFileRoute('/planner')({
  component: PlannerRoute,
});
