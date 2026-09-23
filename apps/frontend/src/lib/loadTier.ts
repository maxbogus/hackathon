/**
 * T-129: colour-tier mapping for predicted passenger load.
 *
 * Lives in its own file (not in EtaCard.tsx) so that EtaCard.tsx only exports
 * React components — required by eslint-plugin-react-refresh for fast refresh
 * to work during `yarn dev`.
 *
 * Bucket boundaries (chosen in T-128):
 *   load < 70          → green   (comfortable)
 *   load 70..90        → yellow  (grey zone)
 *   load 90..110       → red     (crowded)
 *   load 110..∞        → darkred (over capacity)
 */

export type LoadTier = 'green' | 'yellow' | 'red' | 'darkred';

export function loadTier(loadPct: number): LoadTier {
  if (loadPct < 70) return 'green';
  if (loadPct < 90) return 'yellow';
  if (loadPct < 110) return 'red';
  return 'darkred';
}
