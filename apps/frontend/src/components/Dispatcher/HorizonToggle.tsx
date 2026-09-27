/**
 * T-200 (ревизия): 3 кнопки-плашки для горизонта алертов.
 *
 * F-097: раньше UI передавал ``window_min=1440/131400/525600``, но backend
 * ограничивал ``window_min ≤ 120`` (≤1440 после фикса), и эти минуты — не
 * тот же домен, что «3 месяца» или «1 год». Теперь UI отправляет
 * семантический ``horizon=day|month|year`` (через ``apiHorizonFor``),
 * а backend использует его для выбора количества ближайших трамваев
 * (5 / 30 / 60) — это и есть «прогноз на 3 горизонта» из ТЗ задачи 1.
 *
 * Контракт (контрактируем с backend `apps/backend/app/insights/alerts.py`):
 *   value="1d"   onChange={next}   // pure controlled
 *   1d → apiHorizonFor('1d') = 'day'
 *   3m → apiHorizonFor('3m') = 'month'
 *   1y → apiHorizonFor('1y') = 'year'
 */

import { t } from '@/lib/i18n/t';
import type { TKey } from '@/lib/i18n/keys';

export type HorizonKey = '1d' | '3m' | '1y';

export interface HorizonSpec {
  readonly key: HorizonKey;
  readonly apiHorizon: 'day' | 'month' | 'year';
}

export const HORIZONS: ReadonlyArray<HorizonSpec> = [
  { key: '1d', apiHorizon: 'day' },
  { key: '3m', apiHorizon: 'month' },
  { key: '1y', apiHorizon: 'year' },
];

const LABEL_KEY: Readonly<Record<HorizonKey, string>> = {
  '1d': 'dispatcher.alerts.horizon1Day',
  '3m': 'dispatcher.alerts.horizon3Months',
  '1y': 'dispatcher.alerts.horizon1Year',
};

/** API horizon param для бэкенда: day | month | year. */
export function apiHorizonFor(key: HorizonKey): 'day' | 'month' | 'year' {
  const found = HORIZONS.find((h) => h.key === key);
  if (!found) throw new Error(`HorizonToggle: unknown key ${key}`);
  return found.apiHorizon;
}

export interface HorizonToggleProps {
  readonly value: HorizonKey;
  readonly onChange: (next: HorizonKey) => void;
}

export function HorizonToggle({ value, onChange }: HorizonToggleProps): JSX.Element {
  return (
    <div
      data-testid="horizon-toggle"
      role="group"
      aria-label={t('dispatcher.alerts.horizonGroupLabel')}
      style={{ display: 'inline-flex', gap: 8 }}
    >
      {HORIZONS.map((h) => {
        const selected = h.key === value;
        return (
          <button
            key={h.key}
            type="button"
            onClick={() => {
              if (!selected) onChange(h.key);
            }}
            aria-pressed={selected}
            data-horizon={h.key}
            data-testid={`horizon-${h.key}`}
            style={{
              padding: '8px 16px',
              border: '1px solid #475569',
              borderRadius: 4,
              background: selected ? '#1d4ed8' : 'transparent',
              color: selected ? '#fff' : '#cbd5e1',
              cursor: selected ? 'default' : 'pointer',
              fontSize: 14,
              fontWeight: selected ? 600 : 400,
            }}
          >
            {t(LABEL_KEY[h.key] as TKey)}
          </button>
        );
      })}
    </div>
  );
}
