/**
 * T-203: Horizon + Granularity selector for the predictions chart.
 *
 * The API at /api/v1/predictions/db/{route_id} (T-195) supports:
 *   - horizon: day | month | year
 *   - granularity: hour | day | month
 *
 * Previously these were hard-coded to (day, hour) in <PredictionsChart>.
 * Adding the selectors was a designer-review request (T-203) — without
 * them, the chart could only show one of the three supported horizons.
 *
 * Pure controlled component: parent owns state, child emits onChange.
 */

import { t } from '@/lib/i18n/t';

export type Horizon = 'day' | 'month' | 'year';
export type Granularity = 'hour' | 'day' | 'month';

export interface HorizonGranularityValue {
  readonly horizon: Horizon;
  readonly granularity: Granularity;
}

export interface HorizonGranularityProps {
  readonly horizon: Horizon;
  readonly granularity: Granularity;
  readonly onChange: (next: HorizonGranularityValue) => void;
}

const HORIZONS: ReadonlyArray<Horizon> = ['day', 'month', 'year'];
const GRANULARITIES: ReadonlyArray<Granularity> = ['hour', 'day', 'month'];

/** Translate enum → TKey. The `as const` makes each branch a literal
 *  that satisfies TKey's union (see lib/i18n/keys.ts). */
function horizonLabelKey(h: Horizon) {
  return h === 'day'
    ? ('analyst.horizonDay' as const)
    : h === 'month'
      ? ('analyst.horizonMonth' as const)
      : ('analyst.horizonYear' as const);
}

function granularityLabelKey(g: Granularity) {
  return g === 'hour'
    ? ('analyst.granularityHour' as const)
    : g === 'day'
      ? ('analyst.granularityDay' as const)
      : ('analyst.granularityMonth' as const);
}

export function HorizonGranularity({
  horizon,
  granularity,
  onChange,
}: HorizonGranularityProps): JSX.Element {
  return (
    <div data-testid="horizon-granularity" style={{ display: 'flex', gap: 12 }}>
      <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13 }}>
        <span>{t('analyst.horizonLabel')}</span>
        <select
          aria-label={t('analyst.horizonLabel')}
          value={horizon}
          onChange={(e) => onChange({ horizon: e.target.value as Horizon, granularity })}
          data-testid="horizon-select"
          style={{ padding: '4px 8px' }}
        >
          {HORIZONS.map((h) => (
            <option key={h} value={h}>
              {t(horizonLabelKey(h))}
            </option>
          ))}
        </select>
      </label>

      <label style={{ display: 'flex', flexDirection: 'column', fontSize: 13 }}>
        <span>{t('analyst.granularityLabel')}</span>
        <select
          aria-label={t('analyst.granularityLabel')}
          value={granularity}
          onChange={(e) => onChange({ horizon, granularity: e.target.value as Granularity })}
          data-testid="granularity-select"
          style={{ padding: '4px 8px' }}
        >
          {GRANULARITIES.map((g) => (
            <option key={g} value={g}>
              {t(granularityLabelKey(g))}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
