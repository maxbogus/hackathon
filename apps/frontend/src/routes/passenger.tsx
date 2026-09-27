/**
 * T-135: "/passenger" → <PassengerMode />.
 *
 * T-129: the most important role for the hackathon demo — the passenger.
 * They are the primary beneficiary ("когда приедет и будет ли место?").
 *
 * T-225 / D-037: URL остался /passenger (route НЕ переименован), но в nav
 * эта вкладка теперь называется «Диспетчер» (см. lib/roles.ts). Сама
 * страница PassengerMode — это диспетчерский дашборд «нагрузка по линиям»
 * с двумя блоками actuals + predictions (T-218).
 */

import { createFileRoute } from '@tanstack/react-router';

import { PassengerMode } from '@/pages/PassengerMode';

export const Route = createFileRoute('/passenger')({
  component: PassengerMode,
});
