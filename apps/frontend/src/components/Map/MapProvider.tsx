/**
 * T-122 / D-003: <RouteMap> — фабрика карты (Strategy: OSM ↔ Yandex).
 *
 * Почему файл называется MapProvider, а компонент — RouteMap: D-003 зафиксировал
 * имя файла (паттерн Strategy), а «RouteMap» точнее описывает то, что рендерится
 * (карта маршрутов) и не притворяется React-контекстом.
 *
 * Контракт с остальным приложением — только `<RouteMap {...RouteMapProps} />`
 * (`./types.ts`). Оба провайдера lazy-loaded: в бандл попадает лишь выбранный
 * (React.lazy грузит модуль при первом рендере), см. clinerule 09.
 *
 * Выбор провайдера — `selectMapImpl()` (`./mapStrategy.ts`), чистая функция.
 */

import { Suspense, lazy } from 'react';

import { getStubMessage, getYandexMapsKeyOrNull, loadConfig } from '@/lib/config';
import { t } from '@/lib/i18n/t';

import { MAP_VIEW_HEIGHT } from './mapColors';
import { selectMapImpl } from './mapStrategy';
import type { RouteMapProps } from './types';

const LeafletMap = lazy(() => import('./LeafletMap'));
const YandexMap = lazy(() => import('./YandexMap'));

export function RouteMap({ height = MAP_VIEW_HEIGHT, ...rest }: RouteMapProps): JSX.Element {
  const config = loadConfig();
  // hasYandexKey = реальный ключ (не пусто и не плейсхолдер `your_..._here`).
  const impl = selectMapImpl(config.map.impl, getYandexMapsKeyOrNull() !== null);
  const stubReason = getStubMessage(config.map.yandexMapsKey);
  const yandexRequested = config.map.impl === 'yandex';

  return (
    <section
      data-testid="route-map"
      data-impl={impl}
      aria-label={t('map.ariaLabel')}
      style={{ marginTop: 16 }}
    >
      <h3 style={{ margin: '0 0 8px', color: '#555' }}>{t('map.title')}</h3>

      {rest.routes.length === 0 ? (
        <div
          data-testid="route-map-empty"
          style={{
            height,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#f5f5f5',
            borderRadius: 6,
            color: '#888',
            fontSize: 13,
          }}
        >
          {t('map.empty')}
        </div>
      ) : (
        <Suspense
          fallback={
            <div
              data-testid="route-map-loading"
              style={{
                height,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#f5f5f5',
                borderRadius: 6,
                color: '#888',
                fontSize: 13,
              }}
            >
              {t('common.loading')}
            </div>
          }
        >
          {impl === 'yandex' ? (
            <YandexMap height={height} {...rest} />
          ) : (
            <LeafletMap height={height} {...rest} />
          )}
        </Suspense>
      )}

      {impl === 'osm' && yandexRequested && stubReason !== null && (
        <p
          data-testid="route-map-key-warning"
          style={{ margin: '8px 0 0', color: '#888', fontSize: 12 }}
        >
          {t('map.noKey')}
        </p>
      )}

      <p style={{ margin: '8px 0 0', color: '#888', fontSize: 12 }}>{t('map.hint')}</p>
    </section>
  );
}
