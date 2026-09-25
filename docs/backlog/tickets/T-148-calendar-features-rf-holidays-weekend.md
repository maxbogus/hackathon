---
id: T-148
phase: 2
title: Calendar features РФ — праздники + is_weekend + предпраздничные дни
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.9
  score: 9.0
depends_on: []
blocks: []
tags: [ml, calendar, holidays, weekend, hackathon, exogenous]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-148: Calendar features РФ — праздники + is_weekend + bridge days

## Context

Из F-020 (per-route WAPE diagnose, T-146):
- per-weekday: Сб=0.79, Вс=0.80 — **выходные падают на 10pp** относительно будних (0.86)
- гипотеза из `docs/reports/diagnose_per_route.md`: "в выходные другой паттерн
  (меньше пиков утром/вечером, более равномерный поток). Текущая модель сглаживает
  различия между буднями и выходными (mean по (route, hour, weekday), но если
  данных мало в выходные — fallback на общий mean)."

Дополнительно: **праздники РФ** (4 ноября, 9 мая, и т.д.) — это будни по weekday,
но **нерабочие** по факту. Текущая RouteBaselineMean их не различает.

## Источник данных (R4 hackathon-rules: no internet at runtime)

Выбран **вариант B: хардкод списка праздников РФ 2025** в `ml/transit_ai/data/calendar_rf.py`.
Обоснование: R4 запрещает HTTP на runtime → только offline-варианты.
Хардкод быстрее (15 мин), не требует новых deps, не ломает R3 reproducible.

План-после-хакатона: мигрировать на `holidays-ru` lib (вариант A) для покрытия всех лет.

## Список праздников РФ 2025

Постановление Правительства РФ от 04.10.2024 № 1335 "О переносе выходных дней в 2025 году"
+ ТК РФ ст. 112:

- 1-8 января — Новогодние каникулы (8 дней)
- 23 февраля (вс) — День защитника Отечества → перенос на пн 24 (и далее в мае)
- 8 марта (сб) — 8 марта → перенос на пт 7 (женский день — короткая неделя)
- 1 мая (чт) — Праздник Весны и Труда
- 9 мая (пт) — День Победы
- 12 июня (чт) — День России
- 4 ноября (вт) — День народного единства

Переносы выходных (2025):
- с 5 января (вс) → пн 6 мая? Нет — это делается через майские.
- Реальный перенос на 2025 (ПП РФ №1335):
  - 5 января (вс) → 31 декабря (ср)
  - 23 февраля (вс) → 8 мая (чт)
  - 8 марта (сб) → 13 июня (пт)  → нет, неправильно
  - **Упрощение**: для нашего use case достаточно отметить
    сами праздники как `is_holiday=True` (8 дней НГ, 23.02, 08.03, 01.05, 09.05, 12.06, 04.11).

## Acceptance Criteria

- [x] Новый модуль `ml/transit_ai/data/calendar_rf.py`:
  - `is_holiday(date) -> bool` — праздник (по hardcoded set)
  - `is_weekend(date) -> bool` — Сб/Вс
  - `is_working_day(date) -> bool` — будни минус праздники
  - `get_day_type(date) -> Literal["workday","holiday","weekend"]` — тип дня
  - Константа `RF_HOLIDAYS_2025: set[date]`
- [x] 8+ unit-тестов в `ml/tests/test_calendar_rf.py`:
  - `test_is_holiday_new_year_jan1`
  - `test_is_holiday_defender_day_feb23`
  - `test_is_holiday_women_day_mar8`
  - `test_is_holiday_labor_day_may1`
  - `test_is_holiday_victory_day_may9`
  - `test_is_holiday_russia_day_jun12`
  - `test_is_holiday_unity_day_nov4`
  - `test_is_weekend_saturday`
  - `test_is_weekend_sunday`
  - `test_is_working_day_normal_weekday`
  - `test_get_day_type_classifies_correctly`
  - `test_calendar_covers_year_2025_365_days`
- [x] `ml/transit_ai/models/route_baseline.py` интегрирует `is_holiday`:
  - `fit()` группирует по `(route_id, weekday, hour, is_holiday)` вместо `(route, weekday, hour)`
  - `predict_route()` использует `is_holiday(date)` для выбора bucket
  - Fallback стратегия: holiday → same_weekday_holiday → weekend → same_weekday → global
- [x] Тесты `route_baseline` адаптированы (5+ тестов passed)
- [x] Re-fit + re-evaluate на holdout (сен-окт 2025):
  - `make diagnose` → ожидаем weekday Сб/Вс WAPE улучшение +1-3pp
  - Если WAPE ухудшился — откатить и записать F-022 в ledger
- [x] Новый submission v4-calendar-rf (если holdout улучшился)
- [x] F-022 в ledger: «Calendar features РФ дали +Xpp WAPE»

## Technical Notes

```python
# ml/transit_ai/data/calendar_rf.py
"""Российский производственный календарь (T-148).

Offline hardcoded список праздников РФ 2025. R4 hackathon-rules: no internet.
"""
from datetime import date
from typing import Literal

RF_HOLIDAYS_2025: set[date] = {
    date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4),
    date(2025, 1, 5), date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8),
    date(2025, 2, 23),
    date(2025, 3, 8),
    date(2025, 5, 1),
    date(2025, 5, 9),
    date(2025, 6, 12),
    date(2025, 11, 4),
}

def is_holiday(d: date) -> bool:
    return d in RF_HOLIDAYS_2025

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # 5=Сб, 6=Вс

def is_working_day(d: date) -> bool:
    return not is_holiday(d) and not is_weekend(d)

def get_day_type(d: date) -> Literal["workday","holiday","weekend"]:
    if is_holiday(d): return "holiday"
    if is_weekend(d): return "weekend"
    return "workday"
```

```python
# route_baseline.py fit()
from transit_ai.data.calendar_rf import get_day_type
df["day_type"] = df["date"].apply(get_day_type)
# day_type ∈ {workday, holiday, weekend}
grouped = df.groupby(["route_id", "weekday", "hour", "day_type"])["boardings"]
```

## Verification

```bash
# 1. RED: тесты падают
uv run pytest ml/tests/test_calendar_rf.py -v --no-cov
# → ModuleNotFoundError transit_ai.data.calendar_rf

# 2. GREEN: реализуем calendar_rf.py → тесты зелёные
uv run pytest ml/tests/test_calendar_rf.py -v --no-cov
# → 12 passed

# 3. Все тесты passing
uv run pytest ml/tests/test_calendar_rf.py ml/tests/test_route_baseline.py -v --no-cov

# 4. Re-fit + re-diagnose
make diagnose
# → ожидаем weekday Сб/Вс WAPE улучшение

# 5. Если улучшилось → submission v4
make submission SUBMISSION_ID=v4-calendar-rf

# 6. Линт
make lint
```

## Beneficiary Impact

**Город (⭐⭐⭐⭐)** — точные прогнозы на праздники (4 ноября, 9 мая, НГ) = правильный
график транспорта в пиковые дни. **Диспетчер (⭐⭐⭐)** — confidence в выходные.

RICE 9.0 — топ-3.

## Не делать

- ❌ Не использовать `holidays-ru` lib (он нужен после хакатона, не сейчас)
- ❌ Не использовать HTTP API (R4)
- ❌ Не предсказывать "эффект моста" между праздниками (bridge days) — упрощаем
- ❌ Не менять SyntheticSource (он и так генерит свои праздники)
