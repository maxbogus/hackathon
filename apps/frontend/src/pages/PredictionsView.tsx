/**
 * T-222 follow-up: страница-обёртка над <PredictionsTable>.
 *
 * Ответственность:
 *  - Дёрнуть /api/v1/predictions/export.csv через TanStack Query
 *    (helper lib/predictionsTable.ts).
 *  - Передать rows / isLoading / error в PredictionsTable.
 *  - Показать активную модель + WAPE-score в footer (T-201 pattern).
 *
 * Компонент PredictionsTable остаётся pure UI (D-038.1) — этот файл
 * единственное место, где встречается "fetch + React component".
 */

import { useQuery } from '@tanstack/react-query';

import { t, tf } from '@/lib/i18n/t';
import { PredictionsTable } from '@/components/Passenger';
import {
  predictionsCsvQueryFn,
  predictionsCsvQueryKey,
  PREDICTIONS_CSV_STALE_TIME_MS,
} from '@/lib/predictionsTable';
import { fetchActiveModel, formatWapeScore } from '@/lib/activeModel';
import { modelName } from '@/lib/labels';

export function PredictionsView(): JSX.Element {
  // 5-min cached query (clinerule D-038.2 / R6 SLA).
  const { data, isLoading, error } = useQuery({
    queryKey: predictionsCsvQueryKey,
    queryFn: predictionsCsvQueryFn,
    staleTime: PREDICTIONS_CSV_STALE_TIME_MS,
  });

  // Активная модель для footer (не блокирует рендер — silent fail в lib/activeModel).
  const modelQuery = useQuery({
    queryKey: ['active-model'] as const,
    queryFn: () => fetchActiveModel(),
    staleTime: 60_000,
  });

  const rows = data ?? [];
  const errMessage = error ? (error instanceof Error ? error.message : String(error)) : null;

  // T-231: человекочитаемое имя модели + «Точность (WAPE)» вместо `WAPE-score`.
  const activeModel = modelQuery.data ?? null;
  const activeModelName = activeModel ? modelName(activeModel.model_id, t) || '—' : '—';
  const activeWape = activeModel ? formatWapeScore(activeModel.wape_score) : null;
  const modelLabel = activeModel
    ? activeWape !== null
      ? tf('passenger.activeModelFooter', activeModelName, activeWape)
      : tf('passenger.modelFooter', activeModelName)
    : null;

  return (
    /*
     * T-232: полная ширина и высота. `maxWidth: 1400 + margin auto` убран —
     * таблица занимает всю ширину окна; `flex:1 + minHeight:0` в колонке
     * __root отдаёт таблице всю высоту за вычетом заголовка/фильтров/footer.
     * `<main>` → `<section>`: уровень main уже даёт каркас (__root.tsx),
     * вложенный main был невалидной семантикой.
     */
    <section
      data-testid="predictions-view"
      style={{
        flex: 1,
        minHeight: 0,
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 24px',
      }}
    >
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>{t('predictions.viewTitle')}</h1>
        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 13 }}>
          {t('predictions.viewHint')}
        </p>
      </header>

      {modelLabel && (
        <p
          data-testid="predictions-view-model"
          style={{ marginBottom: 12, fontSize: 13, color: '#475569' }}
        >
          {modelLabel}
        </p>
      )}

      <PredictionsTable rows={rows} isLoading={isLoading} error={errMessage} fillHeight />
    </section>
  );
}
