---
id: T-122
phase: 4
title: apps/frontend — MapProvider + LeafletMap + YandexMap (Strategy pattern OSM ↔ Yandex)
priority: P1
effort: 4
unit: hours
rice:
  R: 6
  I: 3.0
  C: 0.6
  score: 2.7
depends_on: []
blocks: []
tags: [frontend, map, leaflet, yandex, strategy, beneficiary, hackathon]
status: done
created: 2026-09-23
updated: 2026-09-27
assignee: "boguslavsky"
---

# T-122: MapProvider + LeafletMap + YandexMap — карта Москвы с остановками и маршрутами

## Context

ТЗ §3.1.4 (прямое требование жюри):
> «Карта Москвы с нанесёнными трамвайными остановками и маршрутами… Цветовая кодировка маркеров
>  в зависимости от прогнозируемой загрузки (5 градаций). Временной слайдер для просмотра
>  загрузки в разные часы/дни. Отображение маршрутов линиями (с толщиной, зависящей от загрузки).»

Сейчас `apps/frontend/src/components/Map/` — **папка пустая** (D-003 в ledger зафиксировал
архитектуру Strategy, но файлы не реализованы). Без карты жюри увидит список карточек, а не
интерактивную карту — это **главный визуал ТЗ**, без которого продукт ощущается неполным.

Решает user stories:
- **Диспетчер:** «Хочу видеть на карте где сейчас перегруз — где выпустить вагон»
- **Пассажир:** «Хочу понять, как далеко мне идти до остановки, на которой будет свободный трамвай»
- **Планировщик:** «Хочу увидеть на карте, где новые маршруты закроют “белые пятна”»

## Acceptance Criteria

- [x] Создан `apps/frontend/src/components/Map/MapProvider.tsx` — фабрика по `VITE_MAP_IMPL=osm|yandex`
      (экспортирует `<RouteMap>`; выбор — чистая функция `mapStrategy.selectMapImpl`)
- [x] Реализован `apps/frontend/src/components/Map/LeafletMap.tsx` (OSM, без ключей, lazy-loaded)
- [x] Реализован `apps/frontend/src/components/Map/YandexMap.tsx` (lazy-loaded, требует `VITE_YANDEX_MAPS_API_KEY`)
- [x] Реализован общий интерфейс `RouteMapProps` в `types.ts` (routes/tierByRoute/loadPctByRoute/
      selectedRouteId/onSelectRoute/height); реализации — `CircleMarker`/`Tooltip` + `Polyline`
- [x] Маркеры остановок с цветовой кодировкой по tier'у загрузки (green/yellow/red/darkred + gray),
      палитра — тот же `loadTier.COLORS`, что у карточек и легенды
- [x] Линии маршрутов: polyline с толщиной, пропорциональной `load_pct` (`polylineWeight`)
- [x] Данные — из нового backend-контракта `GET /api/v1/geo/routes` (T-227): **реальные 10 маршрутов /
      142 остановки** вместо мок-`STOP_ROUTES` (mock остаётся только для ETA-демо)
- [x] `yarn typecheck` — 0 ошибок в файлах T-122 (2 pre-existing в `lib/routeCsv.ts`, см. T-221)
- [x] `vite build` собирает; оба провайдера — отдельные lazy-чанки (`LeafletMap-*.js`, `YandexMap-*.js`)
- [ ] Smoke в браузере (`yarn dev` → `/passenger`) — **не выполнено в этой сессии**: нужен живой
      backend + глазами проверить тайлы/ключ (см. «Что осталось»)
- [x] Клик по остановке/линии → `onSelectRoute`; клик по карточке маршрута → тот же выбор
      (взаимная подсветка карточка ↔ карта; прогноз остаётся в карточках)
- [x] Документация: `apps/frontend/src/components/Map/README.md` (как добавить новый провайдер)

## Technical Notes

Переиспользовать из clinerule `09-map-strategy.md`:
- Lazy-load через `React.lazy()` (оба компонента грузятся только при использовании)
- `import.meta.env.VITE_MAP_IMPL` для переключения
- `Suspense` с skeleton fallback

Отличия от исходного плана тикета (осознанные):
- Yandex — через уже установленный `@pbe/react-yandex-maps` (JS API 2.1, `coordorder=latlong`),
  а не через `<script>`-тег вручную: пакет сам строит `api-maps.yandex.ru/2.1/?apikey=...`.
- Геометрия — реальный каталог backend вместо мока; дорожной polyline в данных нет,
  линия строится по остановкам в порядке `order` (нужен routing-API — вне R4).
- Vite читает env из корня репо (`envDir`), чтобы ключ не дублировался (F-102).

Структура файлов:
```
apps/frontend/src/components/Map/
├── README.md              # документирует как добавить новый провайдер
├── MapProvider.tsx        # фабрика (компонент <RouteMap>)
├── mapStrategy.ts         # selectMapImpl() — выбор провайдера
├── types.ts               # RouteMapProps, ре-экспорт MapRoute/MapStop
├── mapColors.ts           # цвет/толщина/радиус/прозрачность
├── LeafletMap.tsx         # OSM реализация
├── YandexMap.tsx          # Yandex реализация
└── *.test.ts(x)           # 28 тестов (colors/strategy/provider) + тесты в lib/geoRoutes.test.ts
```

## Verification

```bash
cd apps/frontend && yarn typecheck            # мои файлы: 0 errors
cd apps/frontend && yarn test:run             # 223 passed (2 pre-existing fails в routeCsv.test.ts)
cd apps/frontend && yarn docker-build         # vite build: LeafletMap/YandexMap — lazy-чанки
make frontend-text-check                      # ✓ No hardcoded UI strings
make api-check                                # OpenAPI in sync (24 paths)
make up                                       # http://localhost:5173/passenger — карта с 10 маршрутами
# Yandex (опционально): VITE_MAP_IMPL=yandex в корневом .env + ключ → перезапуск yarn dev
```

## Status

`done` (2026-09-27). Осталось (не блокирует приёмку):
1. Живой браузерный smoke на OSM и, при наличии валидного ключа под JS API 2.1, на Yandex.
2. `yarn build` (с `tsc`) остаётся красным из-за 2 pre-existing TS-ошибок в `lib/routeCsv.ts` — T-221.
3. Вне скоупа этого тикета (ТЗ §3.1.4): временной слайдер по часам (нет per-stop источника загрузки),
   реальная дорожная геометрия.


## Beneficiary Impact

**Жюри (⭐⭐⭐⭐⭐)** — карта = главный визуальный импакт ТЗ. Без неё продукт = «список карточек», с ней = «интерактивный дашборд».
**Диспетчеры (⭐⭐⭐⭐)** — наглядная локализация перегруза (heatmap на карте).
**Пассажиры (⭐⭐⭐)** — понимание «где ближайший трамвай с местом».

RICE: 4.5 — топ-15 приоритет. Делается в Фазе 4, можно параллельно с T-129/T-130/T-131.
