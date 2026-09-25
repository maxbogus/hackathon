"""Russian production calendar (T-148).

Hardcoded список праздников РФ на 2025 год (T-148, F-020, R4 hackathon-rules).

R4: no internet at runtime → нельзя HTTP API (isdayoff.ru, LawMatic).
Решение: офлайн-список праздников в коде. Покрывает только 2025 — этого
достаточно для текущих прогонов (train янв-авг, holdout сен-окт, submission
ноя-дек 2025).

После хакатона: миграция на holidays-ru lib (покрытие 1993-2026).

Источник праздников:
- ТК РФ ст. 112 (редакция 2024) — 7 федеральных праздников
- Постановление Правительства РФ от 04.10.2024 № 1335 — переносы выходных 2025
- Производственный календарь на 2025 (consultant.ru, garant.ru)
"""

from __future__ import annotations

from datetime import date
from typing import Literal

__all__ = [
    "RF_HOLIDAYS_2025",
    "get_day_type",
    "is_holiday",
    "is_weekend",
    "is_working_day",
]

# 14 праздничных дней в 2025 (по 7 праздникам ТК РФ + 7 дней НГ каникул)
RF_HOLIDAYS_2025: set[date] = {
    # Новогодние каникулы (8 дней: 1-8 января)
    date(2025, 1, 1),
    date(2025, 1, 2),
    date(2025, 1, 3),
    date(2025, 1, 4),
    date(2025, 1, 5),
    date(2025, 1, 6),
    date(2025, 1, 7),
    date(2025, 1, 8),
    # День защитника Отечества
    date(2025, 2, 23),
    # Международный женский день
    date(2025, 3, 8),
    # Праздник Весны и Труда
    date(2025, 5, 1),
    # День Победы
    date(2025, 5, 9),
    # День России
    date(2025, 6, 12),
    # День народного единства
    date(2025, 11, 4),
}


def is_holiday(d: date) -> bool:
    """True если d — официальный нерабочий праздничный день РФ (на 2025).

    Выходные Сб/Вс — НЕ считаются праздниками (см. is_weekend).
    Совпадение праздника с Сб/Вс → True (праздник важнее для трафика).
    """
    return d in RF_HOLIDAYS_2025


def is_weekend(d: date) -> bool:
    """True если d — суббота или воскресенье."""
    return d.weekday() >= 5  # 5=Сб, 6=Вс


def is_working_day(d: date) -> bool:
    """True если d — рабочий день (будни минус праздники).

    Рабочий день = (не выходной) AND (не праздник).
    """
    return not is_weekend(d) and not is_holiday(d)


def get_day_type(d: date) -> Literal["workday", "holiday", "weekend"]:
    """Классифицировать день для feature engineering (T-148).

    Приоритет: holiday > weekend > workday.
    Используется как 4-я координата в (route, weekday, hour, day_type)
    для раздельных таблиц средних по типу дня.

    Returns:
        "holiday" — официальный праздник (даже если выпал на Сб/Вс)
        "weekend" — Сб/Вс (если не праздник)
        "workday" — будни (Пн-Пт, если не праздник)
    """
    if is_holiday(d):
        return "holiday"
    if is_weekend(d):
        return "weekend"
    return "workday"
