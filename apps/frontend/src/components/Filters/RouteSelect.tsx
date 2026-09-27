/**
 * T-233: переключатель маршрута на экране «Аналитик».
 *
 * Pure controlled компонент (зеркало `HorizonGranularity`): состояние живёт в
 * `<AnalystDashboard>`, компонент только рисует опции и эмитит `onChange`.
 * В API не ходит — список маршрутов приходит сверху (`lib/routeCatalog.ts`).
 *
 * Заменяет статичную строку «Маршрут: 7», которая была на этом месте до T-233.
 */

import { t, tf } from '@/lib/i18n/t';

export interface RouteSelectProps {
  readonly routes: readonly number[];
  readonly value: number;
  readonly onChange: (routeId: number) => void;
}

export function RouteSelect({ routes, value, onChange }: RouteSelectProps): JSX.Element {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13, marginTop: 8 }}>
      <span>{t('analyst.routeLabel')}</span>
      <select
        aria-label={t('analyst.routeLabel')}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        data-testid="route-select"
        style={{ padding: '4px 8px' }}
      >
        {routes.map((routeId) => (
          <option key={routeId} value={routeId}>
            {tf('analyst.routeOption', routeId)}
          </option>
        ))}
      </select>
    </label>
  );
}
