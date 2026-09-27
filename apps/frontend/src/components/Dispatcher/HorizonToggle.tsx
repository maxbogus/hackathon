/**
 * T-200 (новая редакция): 3 кнопки-плашки для горизонта алертов.
 *
 * Раньше был хардкод DEFAULT_WINDOW_MIN = 30 минут. По запросу 2026-09-27:
 *  - дефолт = 1 день (1440 минут)
 *  - 3 месяца (131400 минут)
 *  - 1 год   (525600 минут)
 *
 * Window_min передаётся в GET /api/v1/insights/alerts как query param.
 *
 * Контракт:
 *   value="1d"   onChange={next}   // pure controlled
 *
 *   1d = 1440 min = 1 день
 *   3m = 131400 min = 3 месяца (90 × 1440)
 *   1y = 525600 min = 1 год   (365 × 1440)
 */

import { t } from '@/lib/i18n/t';

export type HorizonKey = '1d' | '3m' | '1y';

export interface HorizonSpec {
  readonly key: HorizonKey;
  readonly windowMin: number;
}

export const HORIZONS: ReadonlyArray<HorizonSpec> = [
  { key: '1d', windowMin: 1440 },
  { key: '3m', windowMin: 131_400 },
  { key: '1y', windowMin: 525_600 },
];

const LABEL_KEY: Readonly<Record<HorizonKey, string>> = {
  '1d': 'dispatcher.alerts.horizon1Day',
  '3m': 'dispatcher.alerts.horizon3Months',
  '1y': 'dispatcher.alerts.horizon1Year',
};

export function windowMinFor(key: HorizonKey): number {
  const found = HORIZONS.find((h) => h.key === key);
  if (!found) throw new Error(`HorizonToggle: unknown key ${key}`);
  return found.windowMin;
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
            {t(LABEL_KEY[h.key])}
          </button>
        );
      })}
    </div>
  );
}
