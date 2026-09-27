/**
 * T-222 follow-up: /predictions → <PredictionsView> с таблицей прогнозов.
 *
 * T-222 сделал PredictionsTable как переиспользуемый pure UI компонент
 * (apps/frontend/src/components/Passenger/PredictionsTable.tsx, D-038).
 * Этот route — точка входа: подключает helper predictionsCsvQueryFn
 * (5-min TanStack Query cache) и рендерит таблицу.
 *
 * T-223 (3 секции в PassengerMode) отменён, поэтому таблица живёт
 * на отдельном роуте, а не встроена в /passenger (см. F-099).
 */

import { createFileRoute } from '@tanstack/react-router';

import { PredictionsView } from '@/pages/PredictionsView';

export const Route = createFileRoute('/predictions')({
  component: PredictionsView,
});
