/**
 * FiltersPanel — UI для feature_toggles + zero_overrides + coef_* sliders.
 *
 * T-196: использует GET /api/v1/features для списка,
 * POST /api/v1/features/{name}/toggle и /api/v1/zeros/{name}/toggle для переключения.
 *
 * T-231: в UI не протекают внутренние имена (`use_lag`, `zero_route_5`) —
 * подписи берутся из реестра через `lib/labels.ts` (fallback: описание из API).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { t } from '@/lib/i18n/t';
import { featureHint, featureName, zeroHint, zeroName } from '@/lib/labels';

import { customInstance } from '@/api/customInstance';

interface FeatureToggle {
  name: string;
  description: string;
  enabled: boolean;
  is_default: boolean;
}

interface ZeroOverride {
  name: string;
  description: string;
  enabled: boolean;
  params: Record<string, unknown>;
}

interface FeaturesResponse {
  feature_toggles: FeatureToggle[];
  zero_overrides: ZeroOverride[];
}

interface FiltersPanelProps {
  routeId: number;
  coefWeather: number;
  coefEvent: number;
  coefSeason: number;
  onCoefChange: (w: number, e: number, s: number) => void;
}

export function FiltersPanel({
  routeId,
  coefWeather,
  coefEvent,
  coefSeason,
  onCoefChange,
}: FiltersPanelProps) {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['features'],
    queryFn: async () => {
      const data = await customInstance<FeaturesResponse>({
        url: '/api/v1/features',
        method: 'GET',
      });
      return data;
    },
  });

  const toggleFeature = useMutation({
    mutationFn: async (vars: { name: string; enabled: boolean }) => {
      await customInstance({
        url: `/api/v1/features/${vars.name}/toggle`,
        method: 'POST',
        body: { enabled: vars.enabled },
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['features'] }),
  });

  const toggleZero = useMutation({
    mutationFn: async (vars: { name: string; enabled: boolean }) => {
      await customInstance({
        url: `/api/v1/zeros/${vars.name}/toggle`,
        method: 'POST',
        body: { enabled: vars.enabled },
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['features'] }),
  });

  const [localWeather, setLocalWeather] = useState(coefWeather);
  const [localEvent, setLocalEvent] = useState(coefEvent);
  const [localSeason, setLocalSeason] = useState(coefSeason);

  if (isLoading) return <p>{t('common.loading')}</p>;
  if (isError) return <p>{t('common.errorPrefix')}</p>;

  return (
    <aside data-testid="filters-panel" style={{ padding: 16, border: '1px solid #ddd' }}>
      <h2>{t('analyst.filtersTitle')}</h2>
      <p>
        {t('analyst.routeLabel')}: <strong>{routeId}</strong>
      </p>

      <section>
        <h3>{t('analyst.featuresTitle')}</h3>
        {data?.feature_toggles.map((f) => {
          const hint = featureHint(f.name, t);
          return (
            <label key={f.name} style={{ display: 'block', margin: '4px 0' }}>
              <input
                type="checkbox"
                checked={f.enabled}
                onChange={(e) => toggleFeature.mutate({ name: f.name, enabled: e.target.checked })}
                data-testid={`feature-${f.name}`}
              />{' '}
              {featureName(f.name, f.description, t)}{' '}
              {f.is_default && <small>({t('analyst.defaultBadge')})</small>}
              {hint && (
                <>
                  <br />
                  <small style={{ color: '#666' }}>{hint}</small>
                </>
              )}
            </label>
          );
        })}
      </section>

      <section>
        <h3>{t('analyst.zerosTitle')}</h3>
        {data?.zero_overrides.map((z) => {
          const hint = zeroHint(z.name, t);
          return (
            <label key={z.name} style={{ display: 'block', margin: '4px 0' }}>
              <input
                type="checkbox"
                checked={z.enabled}
                onChange={(e) => toggleZero.mutate({ name: z.name, enabled: e.target.checked })}
                data-testid={`zero-${z.name}`}
              />{' '}
              {zeroName(z.name, z.description, t)}
              {hint && (
                <>
                  <br />
                  <small style={{ color: '#666' }}>{hint}</small>
                </>
              )}
            </label>
          );
        })}
      </section>

      <section>
        <h3>{t('analyst.coefsTitle')}</h3>
        <label>
          {t('analyst.coefWeather')}: {localWeather.toFixed(2)}
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.05}
            value={localWeather}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setLocalWeather(v);
              onCoefChange(v, localEvent, localSeason);
            }}
            data-testid="coef-weather"
          />
        </label>
        <label>
          {t('analyst.coefEvent')}: {localEvent.toFixed(2)}
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.05}
            value={localEvent}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setLocalEvent(v);
              onCoefChange(localWeather, v, localSeason);
            }}
            data-testid="coef-event"
          />
        </label>
        <label>
          {t('analyst.coefSeason')}: {localSeason.toFixed(2)}
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.05}
            value={localSeason}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setLocalSeason(v);
              onCoefChange(localWeather, localEvent, v);
            }}
            data-testid="coef-season"
          />
        </label>
      </section>
    </aside>
  );
}
