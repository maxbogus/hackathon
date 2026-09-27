# components/Map — карта маршрутов (T-122, D-003)

Карта трамвайных маршрутов Москвы для дашборда «Диспетчер» (`/passenger`).

## Файлы

| Файл | Роль |
|---|---|
| `MapProvider.tsx` | Публичный компонент `<RouteMap>` — фабрика (Strategy) + `Suspense`/skeleton + пустой каталог |
| `mapStrategy.ts` | `selectMapImpl(impl, hasYandexKey)` — чистая функция выбора провайдера |
| `LeafletMap.tsx` | OSM-реализация (Leaflet/react-leaflet), default, без ключей |
| `YandexMap.tsx` | Yandex-реализация (`@pbe/react-yandex-maps`), требует ключ |
| `mapColors.ts` | Цвет/толщина/радиус/прозрачность; палитра = `lib/loadTier.COLORS` |
| `types.ts` | `RouteMapProps` + ре-экспорт `MapRoute`/`MapStop` из `lib/geoRoutes.ts` |

Данные: `GET /api/v1/geo/routes` (backend, каталог `data/external/stops_routes.json`)
мёржится с `/api/v1/predictions/load` (`lib/geoRoutes.mergeRouteTiers`) — цвет и
толщина линии совпадают с карточками маршрутов.

## Переключение провайдера

```bash
# .env (корень репо — Vite читает его через envDir в vite.config.ts)
VITE_MAP_IMPL=osm            # по умолчанию: Leaflet + OpenStreetMap, без ключей
VITE_MAP_IMPL=yandex         # + VITE_YANDEX_MAPS_API_KEY=<ключ из кабинета Яндекса>
```

Яндекс включится **только** если запрошен в env И ключ реальный (не пустой и
не плейсхолдер `your_..._here`). Иначе — OSM + предупреждение под картой:
демо не должно падать из-за ключа/квоты/Referer-ограничений.

## Как добавить третьего провайдера (например, MapLibre)

1. `MyMap.tsx` — default-export компонент, принимает `RouteMapProps`, рисует
   линии (`polylineWeight`, `mapColorForTier`) и точки (`stopRadius`).
2. `mapStrategy.ts` → расширить `MapImplKind` и `selectMapImpl`.
3. `MapProvider.tsx` → `const MyMap = lazy(() => import('./MyMap'))` + ветка выбора.
4. `ru-RU.ts` → при необходимости добавить ключи в блок `map.*` (ничего
   не хардкодить в `.tsx` — clinerule 20, гейт `make frontend-text-check`).
5. Тест: `MapProvider.test.tsx` — новый env-вариант выбора.

## Известные ограничения

- Геометрия = ломаная по остановкам в порядке `order`. Реального трека по
  дорогам в датасете нет (нужен routing-API — вне R4 «no internet at runtime»).
- В Yandex приглушение невыбранных маршрутов применяется к линиям
  (`strokeOpacity`); пер-объектная прозрачность точек там не выставляется.
- `jsdom` не рендерит карты: тестируются фабрика/цвета/парсинг, живой
  smoke — только в браузере (`yarn dev` → `/passenger`).
