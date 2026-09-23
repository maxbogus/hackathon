/**
 * T-135: "/" → "/passenger" redirect.
 *
 * Why redirect (not just render PassengerMode at "/"):
 *   - URL canonicalisation — the role is always explicit in the URL.
 *   - Browser back from /passenger goes to / (one step), not into the void.
 *   - Sharing the URL "this is the dispatcher view" is unambiguous.
 */

import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    throw redirect({ to: '/passenger' });
  },
});
