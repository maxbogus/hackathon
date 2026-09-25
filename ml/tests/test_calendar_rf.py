"""Tests for Russian calendar features (T-148).

RED phase: эти тесты должны ПАДАТЬ пока ml/transit_ai/data/calendar_rf.py не реализован.
GREEN phase: после реализации все 12 тестов зелёные.

Refs:
- F-020: Сб/Вс WAPE падает на 10pp относительно будних → нужен отдельный bucket
- R4 hackathon-rules: no internet at runtime → hardcoded список праздников
"""

from __future__ import annotations

from datetime import date

import pytest

# ----- is_holiday() ---------------------------------------------------------


@pytest.mark.parametrize(
    "d,expected",
    [
        (date(2025, 1, 1), True),  # Новый год
        (date(2025, 1, 2), True),  # Новогодние каникулы
        (date(2025, 1, 7), True),  # Рождество (по РФ)
        (date(2025, 1, 8), True),  # Последний день каникул
        (date(2025, 2, 23), True),  # День защитника Отечества
        (date(2025, 3, 8), True),  # 8 марта
        (date(2025, 5, 1), True),  # Праздник Весны и Труда
        (date(2025, 5, 9), True),  # День Победы
        (date(2025, 6, 12), True),  # День России
        (date(2025, 11, 4), True),  # День народного единства
        (date(2025, 1, 9), False),  # Четверг после НГ - рабочий
        (date(2025, 4, 15), False),  # Обычный вторник
    ],
)
def test_is_holiday(d: date, expected: bool) -> None:
    from transit_ai.data.calendar_rf import is_holiday

    assert is_holiday(d) is expected


# ----- is_weekend() ---------------------------------------------------------


@pytest.mark.parametrize(
    "d,expected",
    [
        (date(2025, 1, 4), True),  # Сб (не праздник — выходной)
        (date(2025, 1, 11), True),  # Вс (не праздник — выходной)
        (date(2025, 2, 22), True),  # Сб
        (date(2025, 7, 13), True),  # Вс
        (date(2025, 1, 9), False),  # Чт - рабочий
        (date(2025, 5, 1), False),  # Чт - праздник (но НЕ выходной по weekday)
        (date(2025, 6, 12), False),  # Чт - праздник (но НЕ выходной по weekday)
    ],
)
def test_is_weekend(d: date, expected: bool) -> None:
    """is_weekend — чистый weekday check. Праздник на Сб/Вс — отдельная категория
    через is_holiday и get_day_type (holiday > weekend)."""
    from transit_ai.data.calendar_rf import is_weekend

    assert is_weekend(d) is expected


# ----- is_working_day() -----------------------------------------------------


def test_is_working_day_normal_weekday() -> None:
    """Обычный вторник — рабочий день."""
    from transit_ai.data.calendar_rf import is_working_day

    assert is_working_day(date(2025, 4, 15)) is True  # Вт


def test_is_working_day_holiday_returns_false() -> None:
    """9 мая — праздник, не рабочий."""
    from transit_ai.data.calendar_rf import is_working_day

    assert is_working_day(date(2025, 5, 9)) is False


def test_is_working_day_weekend_returns_false() -> None:
    """Сб — выходной, не рабочий."""
    from transit_ai.data.calendar_rf import is_working_day

    assert is_working_day(date(2025, 1, 4)) is False


def test_is_working_day_holiday_on_weekend_returns_false() -> None:
    """Праздник на выходном — всё равно не рабочий."""
    from transit_ai.data.calendar_rf import is_working_day

    # 8 марта 2025 = Сб (и праздник)
    assert is_working_day(date(2025, 3, 8)) is False


# ----- get_day_type() -------------------------------------------------------


def test_get_day_type_workday() -> None:
    from transit_ai.data.calendar_rf import get_day_type

    assert get_day_type(date(2025, 4, 15)) == "workday"  # Вт


def test_get_day_type_weekend() -> None:
    from transit_ai.data.calendar_rf import get_day_type

    # 4 января 2025 = Сб, но это НГ каникулы → должно быть 'holiday'
    # Используем 11 января (Сб, не праздник) для теста 'weekend'
    assert get_day_type(date(2025, 1, 11)) == "weekend"  # Сб вне праздников
    assert get_day_type(date(2025, 1, 12)) == "weekend"  # Вс вне праздников


def test_get_day_type_holiday_on_weekday() -> None:
    """Праздник на буднем дне — приоритет 'holiday'."""
    from transit_ai.data.calendar_rf import get_day_type

    # 4 ноября 2025 = Вт - праздник
    assert get_day_type(date(2025, 11, 4)) == "holiday"


def test_get_day_type_holiday_on_weekend() -> None:
    """Праздник на выходном — приоритет 'holiday'."""
    from transit_ai.data.calendar_rf import get_day_type

    # 8 марта 2025 = Сб (и праздник)
    assert get_day_type(date(2025, 3, 8)) == "holiday"


# ----- Полнота списка праздников --------------------------------------------


def test_calendar_covers_year_2025_365_days() -> None:
    """Каждый день 2025 должен корректно классифицироваться."""
    from transit_ai.data.calendar_rf import get_day_type

    one_day = __import__("datetime").timedelta(days=1)
    d = date(2025, 1, 1)
    end = date(2025, 12, 31)
    n_days = 0
    while d <= end:
        day_type = get_day_type(d)
        assert day_type in ("workday", "holiday", "weekend"), (
            f"{d}: bad type {day_type}"
        )
        n_days += 1
        d += one_day
    assert n_days == 365, f"expected 365 days, got {n_days}"


def test_holidays_count_in_2025() -> None:
    """В 2025 должно быть минимум 14 праздничных дней."""
    from datetime import timedelta

    from transit_ai.data.calendar_rf import is_holiday

    one_day = timedelta(days=1)
    d = date(2025, 1, 1)
    n_holidays = 0
    while d <= date(2025, 12, 31):
        if is_holiday(d):
            n_holidays += 1
        d += one_day
    # 8 (НГ) + 1 (23.02) + 1 (8.03) + 1 (1.05) + 1 (9.05) + 1 (12.06) + 1 (4.11) = 14
    assert n_holidays >= 14, f"expected >=14 holidays, got {n_holidays}"
