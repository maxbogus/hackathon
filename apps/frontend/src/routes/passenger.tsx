/**
 * T-135: "/passenger" → <PassengerMode />.
 *
 * T-129: the most important role for the hackathon demo — the passenger.
 * They are the primary beneficiary ("когда приедет и будет ли место?").
 */

import { createFileRoute } from '@tanstack/react-router';

import { PassengerMode } from '@/pages/PassengerMode';

export const Route = createFileRoute('/passenger')({
  component: PassengerMode,
});
