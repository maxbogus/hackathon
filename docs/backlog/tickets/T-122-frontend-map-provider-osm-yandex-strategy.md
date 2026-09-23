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
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "baev"
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

- [ ] Создан `apps/frontend/src/components/Map/MapProvider.tsx` — фабрика по `VITE_MAP_IMPL=osm|yandex`
- [ ] Реализован `apps/frontend/src/components/Map/LeafletMap.tsx` (OSM, без ключей, lazy-loaded)
- [ ] Реализован `apps/frontend/src/components/Map/YandexMap.tsx` (lazy-loaded, требует VITE_YANDEX_MAPS_API_KEY)
- [ ] Реализован общий интерфейс `MapProvider` (addStopMarker, removeStopMarker, flyTo, onClick) в `types.ts`
- [ ] Маркеры остановок с цветовой кодировкой по `load_color()` (green/yellow/red/darkred)
- [ ] Линии маршрутов: polyline с толщиной, пропорциональной `predicted_load_pct`
- [ ] Используются данные из `STOP_ROUTES` backend (через mock для MVP, через API позже)
- [ ] `yarn typecheck` (`tsc --noEmit`) без ошибок
- [ ] `yarn build` собирает без warnings о circular imports
- [ ] Smoke: `yarn dev` → открыть `http://localhost:5173/?role=dispatcher` → видна карта Москвы с 4 остановками (мин. demo)
- [ ] При клике на маркер — popup с прогнозом загрузки (через alert placeholder)
- [ ] Документация: README в `apps/frontend/src/components/Map/README.md` (как добавить новый провайдер)

## Technical Notes

Переиспользовать из clinerule `09-map-strategy.md`:
- Lazy-load через `React.lazy()` (оба компонента грузятся только при использовании)
- `import.meta.env.VITE_MAP_IMPL` для переключения
- `Suspense` с skeleton fallback

Установка зависимостей (yarn 4 через corepack):
```bash
yarn workspace @transit-ai/frontend add react-leaflet@4 leaflet@1.9
yarn workspace @transit-ai/frontend add -D @types/leaflet
# Yandex Maps JS API грузится через <script> tag (не npm), см. .clinerules/09-map-strategy.md
```

Структура файлов:
```
apps/frontend/src/components/Map/
├── README.md              # документирует как добавить новый провайдер
├── MapProvider.tsx        # фабрика
├── types.ts               # MapProvider interface, Stop, MarkerOptions, ColorScale
├── LeafletMap.tsx         # OSM реализация
└── YandexMap.tsx          # Yandex реализация (скелет достаточно для MVP)
```

Переиспользовать `lib/recommend.ts` и `forecast/load.py::load_color()` (D-012):
- Цвет маркера = `load_color(load_pct)` из backend (или локально через `lib/recommend.ts`)
- Сегменты polyline окрашиваются по тому же принципу

## Verification

```bash
# 1. Type-check
cd apps/frontend && yarn typecheck
# Ожидаем: 0 errors

# 2. Build
cd apps/frontend && yarn build
# Ожидаем: dist/ собран без warnings

# 3. Unit-тесты (если добавим vitest для MapProvider)
cd apps/frontend && yarn test --run MapProvider
# Ожидаем: фабрика выбирает OSM если VITE_MAP_IMPL=osm, Yandex если =yandex

# 4. Live smoke
cd apps/frontend && yarn dev
# Открыть http://localhost:5173 → role=dispatcher → видна карта с 4 остановками
# Кликнуть на маркер stop_id=1 → popup с прогнозом загрузки

# 5. Переключение на Yandex
echo "VITE_MAP_IMPL=yandex" >> apps/frontend/.env.local
echo "VITE_YANDEX_MAPS_API_KEY=$KEY" >> apps/frontend/.env.local
# Перезапустить yarn dev, проверить что грузится Yandex (нужен реальный ключ)
```

## Beneficiary Impact

**Жюри (⭐⭐⭐⭐⭐)** — карта = главный визуальный импакт ТЗ. Без неё продукт = «список карточек», с ней = «интерактивный дашборд».
**Диспетчеры (⭐⭐⭐⭐)** — наглядная локализация перегруза (heatmap на карте).
**Пассажиры (⭐⭐⭐)** — понимание «где ближайший трамвай с местом».

RICE: 4.5 — топ-15 приоритет. Делается в Фазе 4, можно параллельно с T-129/T-130/T-131.
