# 09-map-strategy.md — Переключение карт OSM ↔ Yandex

## Зачем Strategy

Хакатон может предоставить (или не предоставить) Yandex Maps API ключ.
На скелете делаем OSM (бесплатно, без ключей), переключение — через env.

## Паттерн

```typescript
// apps/frontend/src/components/Map/MapProvider.tsx
import { lazy, Suspense } from 'react';

type MapImpl = 'osm' | 'yandex';

// Lazy load — оба компонента грузятся только при использовании
const LeafletMap = lazy(() => import('./LeafletMap'));
const YandexMap = lazy(() => import('./YandexMap'));

const impl = (import.meta.env.VITE_MAP_IMPL ?? 'osm') as MapImpl;

export function MapProvider(props: MapProps) {
  return (
    <Suspense fallback={<MapSkeleton />}>
      {impl === 'osm' ? <LeafletMap {...props} /> : <YandexMap {...props} />}
    </Suspense>
  );
}
```

## Конфигурация (.env)

```bash
# apps/frontend/.env (gitignored)
VITE_MAP_IMPL=osm                     # по умолчанию

# Переключение
VITE_MAP_IMPL=yandex                  # когда есть ключ

# Yandex ключи
VITE_YANDEX_MAPS_API_KEY=...          # получен для хакатона
VITE_YANDEX_GEOCODER_API_KEY=...
```

## API каждого провайдера

Общий интерфейс (для компонентов):

```typescript
// apps/frontend/src/components/Map/types.ts
export interface MapProvider {
  addStopMarker(stop: Stop, options: MarkerOptions): void;
  removeStopMarker(stopId: number): void;
  updateMarkerColor(stopId: number, color: ColorScale): void;
  flyTo(lat: number, lon: number, zoom: number): void;
  onClick(callback: (latlng: LatLng) => void): void;
  destroy(): void;
}

export interface Stop {
  id: number;
  name: string;
  lat: number;
  lon: number;
  routeIds: number[];
}

export type ColorScale = 'green' | 'yellow' | 'orange' | 'red' | 'darkred';

export interface MarkerOptions {
  tooltip?: string;
  popup?: string;
  color: ColorScale;
  cluster?: boolean;
}
```

## Реализация для OSM (Leaflet)

```typescript
// apps/frontend/src/components/Map/LeafletMap.tsx
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export class LeafletProvider implements MapProvider {
  private map: L.Map;
  private markers = new Map<number, L.Marker>();

  constructor(container: HTMLElement, center: [number, number], zoom: number) {
    this.map = L.map(container).setView(center, zoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(this.map);
  }

  addStopMarker(stop: Stop, options: MarkerOptions): void {
    const color = colorToHex(options.color);
    const icon = L.divIcon({
      className: 'stop-marker',
      html: `<div style="background:${color};...">${stop.name}</div>`,
    });
    const marker = L.marker([stop.lat, stop.lon], { icon }).addTo(this.map);
    this.markers.set(stop.id, marker);
  }

  // ... остальные методы
}
```

## Реализация для Yandex

```typescript
// apps/frontend/src/components/Map/YandexMap.tsx
export class YandexProvider implements MapProvider {
  private map: ymaps.Map;
  private markers = new Map<number, ymaps.Placemark>();

  constructor(container: HTMLElement, center: [number, number], zoom: number) {
    this.map = new ymaps.Map(container, { center, zoom, controls: ['zoomControl'] });
  }

  addStopMarker(stop: Stop, options: MarkerOptions): void {
    const placemark = new ymaps.Placemark(
      [stop.lat, stop.lon],
      { hintContent: stop.name },
      { preset: `islands#${colorToYandexPreset(options.color)}CircleIcon` }
    );
    this.map.geoObjects.add(placemark);
    this.markers.set(stop.id, placemark);
  }

  // ... остальные методы
}
```

## Геокодер

Аналогичная Strategy в `apps/frontend/src/api/geocode.ts`:

```typescript
type Geocoder = 'yandex' | 'nominatim';
const geocoder = (import.meta.env.VITE_GEOCODER ?? 'nominatim') as Geocoder;
```

Nominatim (OSM) — бесплатный, но с rate-limit (1 req/sec). Yandex — без лимита при наличии ключа.

## Поиск организаций

Аналогично в `apps/frontend/src/api/search.ts`:

```typescript
type SearchProvider = 'overpass' | '2gis' | 'yandex';
```

- `overpass` (OSM) — бесплатно, без ключей
- `2gis` — бесплатно до 1000/день (нужен ключ на dev.2gis.ru)
- `yandex` — платно, но есть ключ (получен для хакатона)
