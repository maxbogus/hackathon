/**
 * T-226: /historical → <HistoricalView> с таблицей исторических данных.
 *
 * Зеркало routes/predictions.tsx (T-222). TanStack Router file-based:
 * имя файла = путь URL, default export = Route.
 */

import { createFileRoute } from '@tanstack/react-router';

import { HistoricalView } from '@/pages/HistoricalView';

export const Route = createFileRoute('/historical')({
  component: HistoricalView,
});
