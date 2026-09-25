---
id: T-172
phase: 2
title: Events features — инфраструктурные открытия сентября-октября 2025 (Троицкая, кампус Бауманки, route 90, стадион Металлург, ТРЦ Краски)
priority: P1
effort: 2
unit: hours
rice:
  R: 8
  I: 2.5
  C: 0.7
  score: 7.00
depends_on: [T-156, T-160, T-161, T-162, T-168]
blocks: [T-173]
tags: [ml, feature-engineering, events, infrastructure, hackathon-context]
status: in-progress
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-172: Events features для инфраструктурных изменений сентября-октября 2025

## Context

Хакатон оценивает прогноз на **ноябрь–декабрь 2025**. В сентябре–октябре 2025
в Москве произошли значимые инфраструктурные изменения, которые **смещают
пассажиропоток**:

1. **Троицкая линия метро** (открыта 13.09.2025): станции Вавиловская,
   Академическая, Крымская, ЗИЛ. Перераспределяет трафик между наземным
   транспортом и метро в юго-западном секторе.
2. **Трамвайный маршрут №90** (запущен 15.09.2025): Сокольники → Павелецкий,
   через три вокзала, ~15 тыс. пасс/день за первую неделю.
3. **Кампус МГТУ им. Баумана** (открыт сентябрь 2025): 14 зданий, 2 тыс.
   студентов в общежитиях → устойчивый рост трафика на **route 50** (Бауманская).
4. **Стадион «Металлург»** (реконструкция завершена 04.09.2025): домашняя
   арена студентов Бауманки → событийный трафик.
5. **ТРЦ «Краски»** в Некрасовке (открыт октябрь 2025): 62.6 тыс. м²,
   новый районный аттрактор (не наш маршрут, но учтём глобально).
6. **Новые остановки** (10.09.2025): на маршрутах 7, 13, 37, 50 — Каланчёвская,
   Площадь трёх вокзалов (МЦД).
7. **Перенос остановок на приподнятые платформы** (11.10.2025): маршруты
   11, 12, 13, 23, 25, 27, 30, 32, 36, 37, 46, 50 — Бориса Галушкина,
   Семёновская, пр. Будённого.
8. **15 поликлиник после реконструкции** (сентябрь–октябрь 2025): Дорогомилово,
   Красносельский, Москворечье-Сабурово — увеличение локального трафика.

Эти изменения произошли **после окончания train-периода (август 2025)**, поэтому
модель на train **не видела их эффекта**. Но holdout (сентябрь–октябрь) уже
**включает** часть эффектов (Троицкая, кампус Бауманки, route 90) — поэтому
добавление этих фичей должно улучшить holdout WAPE-score.

На **submission period** (ноябрь–декабрь) эффекты продолжаются:
- Стационарный трафик от кампуса Бауманки (работает ежедневно)
- Ramp-up от Троицкой (по Tproekt: рост с 42% до 95 тыс/день к концу года)
- Событийный трафик от стадиона «Металлург» (домашние матчи)
- Pre-holiday эффекты ноября–декабря

## Decision

**8 событий** в `data/external/events_moscow.json`, **decay-weighted фичи** в
`ml/transit_ai/data/events_calendar.py`:

- `event_metro_troitskaya_30d` = `exp(-days_since / 30)` если event_date в последние 60 дней, иначе 0
- `event_baumana_campus_30d` = `exp(-days_since / 30)` (нет decay — постоянный)
- `event_route_90_active` = 1 если event_date ≤ date, иначе 0
- `n_events_active_30d` = count активных событий с весом > 0.5

Decay-форма: **exp(-Δt / τ)** с τ = 30 дней. Это плавный переход без sharp cut-off.
На train-периоде (янв–август) все event-флаги = 0 (событий ещё не было).
На holdout (сен–окт) — флаги активны, что должно помочь модели объяснить новый трафик.

**Маппинг event → route** через поле `affected_routes`:
- Кампус Бауманки → `[50]`
- Route 90 → `[12, 25, 28]` (через Сокольники)
- Остановки Каланчёвская/МЦД → `[7, 11, 12, 13, 25, 37, 50]`
- Перенос платформ → `[11, 12, 13, 25, 27, 30, 37, 50]`
- Троицкая линия → `[]` (глобально, ни один из наших 10 маршрутов не проходит
  рядом с Троицкой по `stops_routes.json`, проверено)
- Стадион Металлург → `[50]` (Бауманская)
- ТРЦ Краски → `[]` (Некрасовка, не наши маршруты)
- Поликлиники → `[]` (нет координат в нашем каталоге)

Для **route-affected** событий: фича умножается на `is_target_route` (0/1).
Для **глобальных**: фича применяется ко всем маршрутам.

## Acceptance Criteria

- [ ] `data/external/events_moscow.json` — 8 событий, поля:
      `id`, `date`, `category`, `magnitude`, `tau_days`, `affected_routes`, `notes`
- [ ] `ml/transit_ai/data/events_calendar.py`:
      - [ ] `load_events() -> list[dict]`
      - [ ] `get_event_features(date: date, route_id: int) -> dict[str, float]` — 4 фичи
      - [ ] `EVENT_FEATURE_NAMES: tuple[str, ...]` — порядок фичей
- [ ] `ml/transit_ai/models/xgboost_route.py`:
      - [ ] `_EVENTS_FEATURES` импортирован
      - [ ] Добавлен в `FEATURE_NAMES` ПОСЛЕ `_POI_FEATURES`, ДО `lag_*`
      - [ ] `_make_features` принимает date column и возвращает event-фичи
- [ ] `ml/tests/test_events_calendar.py` — минимум 4 теста:
      - [ ] `test_event_in_decay_window` — event в пределах τ дней → flag > 0
      - [ ] `test_event_outside_decay_window` — event после τ дней → flag = 0
      - [ ] `test_event_route_targeting` — affected_routes=[50] → flag > 0 для route 50, = 0 для route 25
      - [ ] `test_event_global_applies_to_all_routes` — affected_routes=[] → flag > 0 для всех
- [ ] `make check-all` зелёный (ruff + mypy + pytest)
- [ ] `ml/scripts/train_xgboost.py` запускается с `--model-id xgboost_v9_events`
- [ ] `ml/scripts/make_submission.py` запускается с `--model-id xgboost_v9_events`
- [ ] SUBMISSION CANDIDATE block выводится, manifest.json создан
- [ ] Если holdout WAPE-score > 0.8751 (best so far, T-168): залить на платформу
- [ ] Если holdout WAPE-score ≤ 0.8751: НЕ заливать, F-NNN в ledger

## Technical Notes

**Source files:**
- `data/external/events_moscow.json` — новый
- `ml/transit_ai/data/events_calendar.py` — новый (по образцу `seasonal_calendar.py`)
- `ml/transit_ai/models/xgboost_route.py` — добавить `_EVENTS_FEATURES` в tuple FEATURE_NAMES
  и в `_make_features` — append к DataFrame

**Размер фичи:** 4 новых поля × 14640 строк = negligible.

**Decay function:**
```python
import math
def _decay(days_since: float, tau: float) -> float:
    return math.exp(-max(0.0, days_since) / tau) if days_since >= 0 else 0.0
```

**Edge case:** event_date > date → days_since отрицательный → flag = 0.

## Verification

```bash
make test
uv run --directory ml pytest tests/test_events_calendar.py -v
uv run --directory ml python scripts/train_xgboost.py \
  --start-date 2025-01-01 --end-date 2025-08-31 \
  --holdout-start 2025-09-01 --holdout-end 2025-10-31 \
  --model-id xgboost_v9_events
# Сравнить holdout WAPE-score с предыдущим best 0.8751

uv run --directory ml python scripts/make_submission.py \
  --model-id xgboost_v9_events --submission-id v9-events
# → SUBMISSION CANDIDATE block, manifest.json
# Если READY_TO_UPLOAD → залить, F-NNN в ledger
```

## Status

`ready` → `in-progress` → `done` (после заливки или осознанного отказа)
