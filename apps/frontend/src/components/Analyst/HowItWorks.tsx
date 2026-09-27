/**
 * HowItWorks — короткое объяснение флоу на экране «Аналитик» (T-230).
 *
 * Зачем: пользователь не должен угадывать, почему график не изменился после
 * нажатия «Сгенерировать» (расчёт идёт в фоне, а данные подменяются только
 * после подтверждения). Свёрнуто по умолчанию — не мешает, но объясняет.
 */

import type { TKey } from '@/lib/i18n/keys';
import { t } from '@/lib/i18n/t';

const STEPS: readonly TKey[] = [
  'analyst.howItWorksStep1',
  'analyst.howItWorksStep2',
  'analyst.howItWorksStep3',
  'analyst.howItWorksStep4',
  'analyst.howItWorksStep5',
];

export function HowItWorks(): JSX.Element {
  return (
    <details
      data-testid="how-it-works"
      style={{
        marginBottom: 16,
        padding: '8px 12px',
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: 4,
      }}
    >
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
        {t('analyst.howItWorksTitle')}
      </summary>
      <ul style={{ listStyle: 'none', margin: '8px 0 0 0', paddingLeft: 0, fontSize: 13 }}>
        {STEPS.map((key) => (
          <li key={key} style={{ marginBottom: 4 }}>
            {t(key)}
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: '#475569', marginTop: 6 }}>{t('analyst.howItWorksNote')}</p>
    </details>
  );
}
