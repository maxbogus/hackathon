"""Tests for seasonal_calendar.py (T-160).

RED-тесты пишутся ДО реализации (clinerule 16).
Школьные каникулы, начало учёбы, периоды отпусков — всё критично для
прогноза ноябрь-декабрь 2025 (см. F-029 hard rule).
"""

from __future__ import annotations

from datetime import date

from transit_ai.data.seasonal_calendar import (
    days_to_new_year,
    days_to_school_start,
    get_seasonal_features,
    is_mass_vacation,
    is_pre_holiday,
    is_school_break,
    is_school_start_day,
    is_workday_calendar_rf,
    uni_session_active,
)


def test_is_school_break_october_november_2025() -> None:
    """T-160: осенние каникулы 27.10-04.11 включительно."""
    assert is_school_break(date(2025, 10, 27))
    assert is_school_break(date(2025, 10, 31))
    assert is_school_break(date(2025, 11, 1))
    assert is_school_break(date(2025, 11, 4))
    # Не в каникулах
    assert not is_school_break(date(2025, 11, 5))
    assert not is_school_break(date(2025, 11, 15))


def test_is_school_break_winter_jan_2025() -> None:
    """T-160: зимние каникулы 01.01-08.01 (есть в train)."""
    assert is_school_break(date(2025, 1, 1))
    assert is_school_break(date(2025, 1, 8))
    assert not is_school_break(date(2025, 1, 9))


def test_is_school_break_winter_dec_jan_2025_2026() -> None:
    """T-160: зимние каникулы 25.12.2025-08.01.2026."""
    assert is_school_break(date(2025, 12, 25))
    assert is_school_break(date(2025, 12, 31))
    assert is_school_break(date(2026, 1, 1))
    assert is_school_break(date(2026, 1, 8))
    assert not is_school_break(date(2026, 1, 9))


def test_is_school_start_day_november_5() -> None:
    """T-160: 5 ноября — первый день после осенних каникул (резкий всплеск)."""
    assert is_school_start_day(date(2025, 11, 5))
    assert not is_school_start_day(date(2025, 11, 6))
    assert not is_school_start_day(date(2025, 11, 4))


def test_is_school_start_day_january_9() -> None:
    """T-160: 9 января — после НГ каникул."""
    assert is_school_start_day(date(2025, 1, 9))
    # 13.01 не school_start (только 9.01)


def test_is_school_start_day_september_1() -> None:
    """T-160: 1 сентября — начало учебного года."""
    assert is_school_start_day(date(2025, 9, 1))


def test_is_mass_vacation_dec_jan() -> None:
    """T-160: 25.12-08.01 — массовый отпуск."""
    assert is_mass_vacation(date(2025, 12, 25))
    assert is_mass_vacation(date(2025, 12, 30))
    assert is_mass_vacation(date(2025, 12, 31))
    assert is_mass_vacation(date(2026, 1, 5))
    assert not is_mass_vacation(date(2025, 11, 15))


def test_is_mass_vacation_summer() -> None:
    """T-160: июль-август — летние отпуска (есть в train)."""
    assert is_mass_vacation(date(2025, 7, 1))
    assert is_mass_vacation(date(2025, 8, 31))
    assert not is_mass_vacation(date(2025, 9, 1))


def test_is_pre_holiday_november_3() -> None:
    """T-160: 3 ноября — предпраздничный день (перед 4.11)."""
    assert is_pre_holiday(date(2025, 11, 3))
    assert not is_pre_holiday(date(2025, 11, 4))
    assert not is_pre_holiday(date(2025, 11, 5))


def test_is_pre_holiday_december_31() -> None:
    """T-160: 31 декабря — канун Нового года."""
    assert is_pre_holiday(date(2025, 12, 31))
    assert not is_pre_holiday(date(2025, 12, 30))


def test_days_to_school_start() -> None:
    """T-160: countdown до начала учёбы."""
    # До 5.11 (ближайшее school start): 4 дня
    assert days_to_school_start(date(2025, 11, 1)) == 4
    assert days_to_school_start(date(2025, 11, 4)) == 1
    assert days_to_school_start(date(2025, 11, 5)) == 0
    # Далеко в будущем: до 9.01.2026 — большое число
    assert days_to_school_start(date(2025, 11, 15)) > 50


def test_days_to_new_year() -> None:
    """T-160: countdown до 1 января."""
    assert days_to_new_year(date(2025, 12, 1)) == 31
    assert days_to_new_year(date(2025, 12, 31)) == 1
    assert days_to_new_year(date(2026, 1, 1)) == 365  # до следующего НГ
    assert days_to_new_year(date(2025, 6, 15)) == 200  # ~200 дней до 01.01.2026


def test_is_workday_calendar_rf_november_2025() -> None:
    """T-160: производственный календарь РФ на ноябрь 2025.

    4 ноября — праздник (вт).
    1 ноября (сб) — выходной.
    3 ноября (пн) — рабочий (перенос с 1.11 по ПП №1335).
    """
    assert not is_workday_calendar_rf(date(2025, 11, 1))  # сб
    assert not is_workday_calendar_rf(date(2025, 11, 2))  # вс
    assert is_workday_calendar_rf(date(2025, 11, 3))  # пн (перенос)
    assert not is_workday_calendar_rf(date(2025, 11, 4))  # вт (праздник)
    assert is_workday_calendar_rf(date(2025, 11, 5))  # ср (рабочий)


def test_uni_session_active_december_january() -> None:
    """T-160: зимняя сессия 08.12.2025-25.01.2026."""
    assert not uni_session_active(date(2025, 12, 7))
    assert uni_session_active(date(2025, 12, 8))
    assert uni_session_active(date(2025, 12, 31))
    assert uni_session_active(date(2026, 1, 25))
    assert not uni_session_active(date(2026, 1, 26))


def test_get_seasonal_features_returns_dict() -> None:
    """T-160: get_seasonal_features возвращает все 9 фичей."""
    d = date(2025, 11, 5)  # после осенних каникул, рабочий
    feats = get_seasonal_features(d)
    expected_keys = {
        "is_school_break",
        "is_school_start_day",
        "is_mass_vacation",
        "is_pre_holiday",
        "days_to_school_start",
        "days_to_new_year",
        "is_workday_calendar_rf",
        "uni_session_active",
    }
    assert expected_keys.issubset(set(feats.keys())), (
        f"missing: {expected_keys - set(feats.keys())}"
    )
    assert feats["is_school_break"] == 0  # 5.11 — первый рабочий
    assert feats["is_school_start_day"] == 1  # 5.11 — начало учёбы
    assert feats["is_workday_calendar_rf"] == 1  # 5.11 — рабочий день
    assert feats["uni_session_active"] == 0  # до 8.12


def test_get_seasonal_features_for_submission_period() -> None:
    """T-160: проверяем все дни ноя-дек для стабильности."""
    import pandas as pd

    days = pd.date_range("2025-11-01", "2025-12-31")
    for d in days:
        feats = get_seasonal_features(d.date())
        # Все поля должны быть int (0/1) кроме days_*
        for k, v in feats.items():
            assert isinstance(v, (int, float)), f"{k}={v} is not numeric"
            assert v >= 0, f"{k}={v} < 0"
