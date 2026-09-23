/**
 * T-135: "/analyst" → <PlaceholderPanel role="analyst" />.
 *
 * Analyst dashboards (charts, metrics) will land later — placeholder
 * shows the role label and a "coming soon" hint. See lib/i18n/ru-RU.ts.
 */

import { createFileRoute } from '@tanstack/react-router';

import { PlaceholderPanel } from '@/components/Layout/PlaceholderPanel';
import { ROLES, type RoleDef } from '@/lib/roles';

const ANALYST_ROLE: RoleDef | undefined = ROLES.find((r) => r.id === 'analyst');
if (!ANALYST_ROLE) {
  throw new Error('lib/roles.ts: analyst role is missing — invariant broken');
}

function AnalystRoute(): JSX.Element {
  // After the throw above, TS still widens the type to `RoleDef | undefined`
  // because ROLES.find returns `RoleDef | undefined`. The narrowing happens
  // in the if-block but not across function boundaries, so we re-narrow here.
  if (!ANALYST_ROLE) {
    throw new Error('unreachable');
  }
  return <PlaceholderPanel role={ANALYST_ROLE} />;
}

export const Route = createFileRoute('/analyst')({
  component: AnalystRoute,
});
