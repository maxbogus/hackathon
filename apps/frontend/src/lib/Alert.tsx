/**
 * T-129: minimal homegrown <Alert> component.
 *
 * Why not MUI? We only need a single visual primitive (severity-coloured
 * banner) for the passenger-mode recommendation. Pulling in @mui/material
 * would add ~80 KB to the bundle and force a theme provider. This shim is
 * ~30 lines, has zero dependencies, and styles itself via inline data-*
 * attributes that we can later restyle without changing the API.
 *
 * Severity mapping (matches recommend.ts in src/lib/recommend.ts):
 *  - success → green border + ✅ icon
 *  - warning → amber border + ⚠️ icon
 *  - info    → blue border + ❓ icon (no-data fallback)
 */

import type { ReactNode } from 'react';

import type { Severity } from './recommend';

export interface AlertProps {
  /** Visual style + icon. */
  severity: Severity;
  /** Text content (Russian in our MVP). */
  children: ReactNode;
  /**
   * Optional emoji/icon shown before the text. If omitted, a default per
   * severity is rendered.
   */
  icon?: string;
  /** Override the test id (for E2E/Storybook). */
  testId?: string;
}

const DEFAULT_ICONS: Record<Severity, string> = {
  success: '✅',
  warning: '⚠️',
  info: '❓',
};

const STYLE_BY_SEVERITY: Record<Severity, { bg: string; border: string }> = {
  success: { bg: '#e8f5e9', border: '#2e7d32' },
  warning: { bg: '#fff8e1', border: '#f9a825' },
  info: { bg: '#e3f2fd', border: '#1976d2' },
};

export function Alert({ severity, children, icon, testId }: AlertProps): JSX.Element {
  const style = STYLE_BY_SEVERITY[severity];
  const effectiveIcon = icon ?? DEFAULT_ICONS[severity];

  return (
    <div
      role="status"
      data-severity={severity}
      data-testid={testId}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 16px',
        margin: '12px 0',
        background: style.bg,
        borderLeft: `4px solid ${style.border}`,
        borderRadius: 4,
        fontSize: 16,
        lineHeight: 1.4,
      }}
    >
      <span aria-hidden="true" style={{ fontSize: 20 }}>
        {effectiveIcon}
      </span>
      <span>{children}</span>
    </div>
  );
}
