---
id: T-231
phase: 4
title: Department-grade UI copy revision (4 screens + glossary)
priority: P1
effort: 6
unit: hours
rice:
  R: 3
  I: 1.0
  C: 0.5
  score: 0.25
depends_on: []
blocks: []
tags: [frontend, ux, i18n, copy]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

# T-231: Department-grade UI copy revision (4 screens + glossary)

## Context

Заказчик (внедрение в Департамент транспорта) провёл ревизию текстов интерфейса
и выдал список замечаний по 4 экранам. Интерфейс выглядит как «сырой прототип
для хакатона»: в UI протекают внутренние идентификаторы (`use_lag`, `with_all`,
`zeros=ON`, `baseline_v1`, `test_submission_baseline`), англицизмы (`boardings`,
`WAPE-score`, «Фичи»), панибратский тон («и езжайте») и обрезанные заголовки
(«Мар...»).

Правила проекта уже требуют держать все строки в реестре (clinerule 20), поэтому
основная работа — значения в `lib/i18n/ru-RU.ts` + мэппинг идентификаторов
`backend → TKey` в `lib/labels.ts` (без изменения БД).

## Acceptance Criteria

### Глобально
- [x] `passenger.activeModelFooter` / `modelFooter` показывают «Точность (WAPE)» и
      человекочитаемое имя модели, а не `baseline_v1` / `WAPE-score`
- [x] raw `model_id` доступен в tooltip (`title=`) — трассируемость сохранена
- [x] `common.unitPeople = 'чел.'`; карточка маршрута показывает «754 чел.»
- [x] `RouteLoadCard` / таблицы используют `tf('map.routeLabel', id)` вместо
      хардкода `Маршрут ${id}` (в т.ч. `aria-label` чекбоксов)

### Экран 1 «Исторические данные»
- [x] `historical.viewHint` без «(из БД)»
- [x] заголовок колонки «Факт.» → «Факт. посадки (чел.)»
- [x] колонка «Маршрут» больше не обрезается (grid 70px → 110px в обеих таблицах)
- [x] кнопка чекбоксов «Выбрать все» (вместо «Показать все»)

### Экран 2 «Прогноз — таблица»
- [x] `predictions.viewHint` без «(из БД)»/«поиск»/«WAPE-score» (F-101: поиска нет)
- [x] заголовок колонки «Прогноз (чел.)»
- [x] footer: «Модель: <имя> · Точность (WAPE): 0.9272 · Обновлено только что»

### Экран 3 «Аналитик»
- [x] «Фичи модели» → «Факторы прогнозирования»
- [x] «Обнуление» → «Исключения»
- [x] хардкод `<h3>Коэффициенты</h3>` → ключ реестра
- [x] чекбоксы фич: «Учитывать события/историю/объекты (POI)/сезонность/трафик/погоду»
      + русские пояснения (вместо `use_*` / английских описаний из БД)
- [x] чекбоксы исключений: «Исключить праздники / Ограничить ночной прогноз /
      Исключить маршрут 5 / Исключить выходные» + русские пояснения
- [x] активный набор: «Активный прогноз: Базовый тестовый (сгенерирован)»,
      «Строк: 14640 · Все факторы · Исключения: вкл.»
- [x] «WAPE-score» → «Точность (WAPE)» в панели кандидата
- [x] кнопка эталона → «Восстановить исходный прогноз» (замечание заказчика:
      «Вернуть эталон» звучит пафосно; «Сбросить настройки» неточно — кнопка
      переключает набор прогнозов, а не параметры)
- [x] график: «Исторические данные (посадки)» (вместо `(boardings)`);
      заголовок прогноза без `(with_all) · zeros=ON` → «· Все факторы · Исключения: вкл.»
- [x] `howItWorksStep{1,3,4,5}` переформулированы (фичи/обнуления/WAPE-score/кнопки)

### Экран 4 «Диспетчер»
- [x] `passenger.modeTitle` → «Пассажиропоток по маршрутам»
- [x] `passenger.modeHint` без «и езжайте»
- [x] «Как было (факт)» / «Как будет (прогноз)» → «Фактическая нагрузка» / «Прогнозируемая нагрузка»
- [x] легенда/подписи карточек: «Перегрузка», «Недогрузка», «Норма», «Нет данных»,
      «Нет прогноза» (полные существительные, заглавная буква)

### Качество
- [x] `lib/labels.ts` покрыт unit-тестами (карта + fallback + де-снейкинг)
- [x] `make frontend-text-check` — чисто
- [x] `yarn test:run`, `yarn typecheck`, `yarn lint` — без новых ошибок
- [x] `MIGRATION.md` обновлён (строка T-231)

## Technical Notes

- clinerule 20: все строки — только в `lib/i18n/ru-RU.ts`; компоненты вызывают
  `t()` / `tf()`. `lib/*.ts` — чистые функции без строк (возвращают `TKey`).
- `lib/labels.ts` (new): `featureLabelKey/featureHintKey/zeroLabelKey/zeroHintKey`
  (`backend name → TKey`, fallback на `name`/`description` из API) +
  `modelLabelKey(model_id)` + `featureSetLabelKey(feature_set)`.
- Идентификаторы: явная карта известных `model_id`/`feature_set`; неизвестные —
  generic де-снейкинг (`xgboost_v8_poi` → «Xgboost v8 poi»), никогда не пусто.
- «Мар...» — не текст, а CSS: `GRID_TEMPLATE_COLUMNS = '70px 120px 60px 1fr'`
  + `padding: 8px 12px` в `PredictionsTable.tsx` / `HistoricalTable.tsx`.
- Мёртвые ключи, найденные попутно (не используются в UI): `analyst.summary*`,
  `passenger.loadTier.*`, `passenger.deviationShort`, `loadTier.COLORS[].text`.
  Не трогаем (вне scope), кроме синхронизации формулировок при необходимости.

## Verification

```bash
cd apps/frontend && yarn test:run && yarn typecheck && yarn lint
make frontend-text-check
make check-all
# глазами:
make up
# http://localhost:5173/historical | /predictions | /analyst | /passenger
```
