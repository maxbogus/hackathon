/**
 * T-218+: легенда цветовой шкалы для пассажирского экрана.
 *
 * Объясняет пользователю что означают цвета карточек маршрутов.
 * Single source of truth — loadTier.COLORS (apps/frontend/src/lib/loadTier.ts).
 *
 * Шкала (асимметричная, см. deviationInfo):
 *   🟢 в норме             |dev| < 15%
 *   🟡 +15..+30%           actual > pred, мягкий warning
 *   🟠 +30..+60%           серьёзный warning
 *   🔴 перегруз +60%+      критично
 *   🔵 недогруз            actual < pred (любой magnitude — info)
 *   ⚪ нет данных          boardings = null
 */

import { t } from '@/lib/i18n/t';

import { COLORS } from '@/lib/loadTier';

export function LoadLegend(): JSX.Element {
  type LegendKey = 'green' | 'yellow' | 'red' | 'darkred' | 'lightblue' | 'gray';
  const items: ReadonlyArray<{
    readonly key: LegendKey;
    readonly testId: string;
  }> = [
    { key: 'green', testId: 'legend-green' },
    { key: 'yellow', testId: 'legend-yellow' },
    { key: 'red', testId: 'legend-red' },
    { key: 'darkred', testId: 'legend-darkred' },
    { key: 'lightblue', testId: 'legend-lightblue' },
    { key: 'gray', testId: 'legend-gray' },
  ];

  return (
    <div
      data-testid="load-legend"
      style={{
        marginTop: 20,
        padding: '10px 12px',
        background: '#fafafa',
        borderRadius: 6,
        border: '1px solid #eee',
        display: 'flex',
        flexWrap: 'wrap',
        gap: 10,
        fontSize: 12,
        color: '#555',
      }}
    >
      <div style={{ width: '100%', fontWeight: 600, color: '#333', marginBottom: 2 }}>
        {t('passenger.legend.title')}
      </div>
      {items.map(({ key, testId }) => {
        const visual = COLORS[key];
        return (
          <span
            key={testId}
            data-testid={testId}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <span
              aria-hidden="true"
              style={{
                display: 'inline-block',
                width: 18,
                height: 18,
                borderRadius: 3,
                background: visual.bg,
                borderTop: `3px solid ${visual.border}`,
              }}
            />
            <span>{visual.label}</span>
            <span style={{ color: '#888' }}>·</span>
            <span>{t(`passenger.legend.${key}`)}</span>
          </span>
        );
      })}
    </div>
  );
}
