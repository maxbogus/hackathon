"""Seasonal calendar (T-160): школа, институт, отпуска, начало учёбы.

Дополняет .clinerules/24 + ml/transit_ai/data/calendar_rf.py (T-148).
calendar_rf.py — только официальные праздники.
seasonal_calendar.py — шире: школьные каникулы, начало семестра,
университетская сессия, период массовых отпусков, pre-holiday эффекты.

Источники (hardcode, без HTTP — R4 hackathon-rules):
- Школьный календарь Москвы 2025 (https://myschool.moscow, school.moscow)
- Приказы Минобрнауки о начале семестра
- Производственный календарь 2025 (consultant.ru)
- ПП РФ от 04.10.2024 N 1335 (переносы выходных)
- Эмпирические данные: летние отпуска (июль-август),
  зимние отпуска (25.12-08.01)

Все фичи детерминированные — вычисляются по дате без внешних запросов.
Использование: XGBoostRoutePredictor (T-163).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

# ────────────────────────────────────────────────────────────────────
# Школьные каникулы 2025-2026
# ────────────────────────────────────────────────────────────────────
# Осенние каникулы — КЛЮЧЕВОЙ сигнал для ноября 2025.
# 27.10.2025 (пн) — 04.11.2025 (пн), затем 5.11 — учёба возобновляется.
SCHOOL_BREAKS: list[tuple[date, date]] = [
    (date(2025, 1, 1), date(2025, 1, 8)),  # Зимние (есть в train)
    (date(2025, 3, 24), date(2025, 3, 31)),  # Весенние (есть в train)
    (date(2025, 10, 27), date(2025, 11, 4)),  # Осенние — КЛЮЧЕВОЕ для ноября
    (date(2025, 12, 25), date(2026, 1, 8)),  # Зимние — КЛЮЧЕВОЕ для декабря
]


def _in_ranges(d: date, ranges: list[tuple[date, date]]) -> bool:
    """True если d попадает хотя бы в один из интервалов (inclusive)."""
    return any(start <= d <= end for start, end in ranges)


# Шаг 0 (T-231): каникулы как данные (normalized/calendar.json), код — фолбэк.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_NORMALIZED_PATH = _REPO_ROOT / "data" / "external" / "normalized" / "calendar.json"


def _load_school_breaks() -> list[tuple[date, date]]:
    """Школьные каникулы: `normalized/calendar.json` → фолбэк hardcode.

    Артефакт пишется ETL (`make external-gen`) из
    `data/external/school_breaks_2025.json`.
    """
    if _NORMALIZED_PATH.exists():
        try:
            payload = json.loads(_NORMALIZED_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return list(SCHOOL_BREAKS)
        items = payload.get("school_breaks")
        if isinstance(items, list) and items:
            try:
                return [
                    (date.fromisoformat(str(start)), date.fromisoformat(str(end)))
                    for start, end in items
                ]
            except (ValueError, TypeError):
                return list(SCHOOL_BREAKS)
    return list(SCHOOL_BREAKS)


def is_school_break(d: date) -> bool:
    """True если d — школьные каникулы (нет занятий)."""
    return _in_ranges(d, _load_school_breaks())


# ────────────────────────────────────────────────────────────────────
# Начало учёбы (после каникул)
# ────────────────────────────────────────────────────────────────────
SCHOOL_START_DAYS: set[date] = {
    date(2025, 1, 9),  # После НГ каникул
    date(2025, 4, 1),  # После весенних каникул
    date(2025, 11, 5),  # После осенних каникул — КЛЮЧЕВОЕ
    date(2025, 9, 1),  # Начало учебного года
}


def is_school_start_day(d: date) -> bool:
    """True если d — первый учебный день после каникул (резкий всплеск трафика)."""
    return d in SCHOOL_START_DAYS


# ────────────────────────────────────────────────────────────────────
# Массовые отпуска
# ────────────────────────────────────────────────────────────────────
MASS_VACATION_RANGES: list[tuple[date, date]] = [
    (date(2025, 7, 1), date(2025, 8, 31)),  # Летние отпуска (есть в train)
    (date(2025, 12, 25), date(2026, 1, 8)),  # Зимние отпуска — КЛЮЧЕВОЕ
]


def is_mass_vacation(d: date) -> bool:
    """True если d — период массовых отпусков (снижение трафика)."""
    return _in_ranges(d, MASS_VACATION_RANGES)


# ────────────────────────────────────────────────────────────────────
# Pre-holiday эффекты
# ────────────────────────────────────────────────────────────────────
PRE_HOLIDAY_DAYS: set[date] = {
    date(2025, 2, 22),  # Перед 23 февраля
    date(2025, 3, 7),  # Перед 8 марта
    date(2025, 4, 30),  # Перед 1 мая
    date(2025, 5, 8),  # Перед 9 мая
    date(2025, 6, 11),  # Перед 12 июня
    date(2025, 11, 3),  # Перед 4 ноября — КЛЮЧЕВОЕ
    date(2025, 12, 31),  # Канун Нового года — КЛЮЧЕВОЕ
}


def is_pre_holiday(d: date) -> bool:
    """True если d — предпраздничный день (сокращённый рабочий, выезды)."""
    return d in PRE_HOLIDAY_DAYS


# ────────────────────────────────────────────────────────────────────
# Countdown до начала учёбы / Нового года
# ────────────────────────────────────────────────────────────────────
def days_to_school_start(d: date) -> int:
    """Дней до ближайшего SCHOOL_START_DAYS >= d (или до следующего года)."""
    candidates = sorted(s for s in SCHOOL_START_DAYS if s >= d)
    if candidates:
        return (candidates[0] - d).days
    # Если нет school_start в этом году — берём первое в следующем
    # (для декабря 2025 это 09.01.2026)
    next_year_starts = [date(d.year + 1, 1, 9)] if (d.year + 1, 1, 9) else []
    if next_year_starts:
        return (next_year_starts[0] - d).days
    return 365  # fallback: далеко


def days_to_new_year(d: date) -> int:
    """Дней до 1 января (countdown). 31 декабря = 1, 1 января = 0."""
    target = date(d.year + 1, 1, 1)
    if d >= target:
        # Если d уже после 1.1 (например 1.01.2026), считаем до 1.01.2027
        target = date(d.year + 2, 1, 1)
    return (target - d).days


# ────────────────────────────────────────────────────────────────────
# Производственный календарь РФ на 2025
# ────────────────────────────────────────────────────────────────────
# Источник: consultant.ru + ПП РФ от 04.10.2024 N 1335
# Учитывает переносы выходных.
HOLIDAYS_2025: set[date] = {
    date(2025, 1, 1),
    date(2025, 1, 2),
    date(2025, 1, 3),
    date(2025, 1, 4),
    date(2025, 1, 5),
    date(2025, 1, 6),
    date(2025, 1, 7),
    date(2025, 1, 8),
    date(2025, 2, 23),
    date(2025, 3, 8),
    date(2025, 5, 1),
    date(2025, 5, 9),
    date(2025, 6, 12),
    date(2025, 11, 4),
}

# Переносы выходных 2025 (по ПП РФ №1335):
# 1 ноября (сб) — выходной. 3 ноября (пн) — рабочий (перенос).
WORKDAY_OVERRIDES_2025: dict[date, bool] = {
    # date: is_workday (True/False)
    date(2025, 11, 3): True,  # Пн = рабочий (перенос с 1.11)
}

# Субботы и воскресенья 2025 — выходные по умолчанию
WEEKEND_DAYS: set[int] = {5, 6}  # 5=Сб, 6=Вс


def is_workday_calendar_rf(d: date) -> bool:
    """True если d — рабочий день по производственному календарю РФ 2025.

    Учитывает:
    - официальные праздники (выходной)
    - выходные Сб/Вс
    - переносы выходных (ПП РФ №1335)
    """
    if d in WORKDAY_OVERRIDES_2025:
        return WORKDAY_OVERRIDES_2025[d]
    if d in HOLIDAYS_2025:
        return False
    return d.weekday() not in WEEKEND_DAYS


# ────────────────────────────────────────────────────────────────────
# Университетская сессия
# ────────────────────────────────────────────────────────────────────
UNI_SESSION_RANGES: list[tuple[date, date]] = [
    (date(2025, 12, 8), date(2026, 1, 25)),  # Зимняя сессия — снижение трафика
    (date(2025, 6, 1), date(2025, 7, 15)),  # Летняя сессия (есть в train)
]


def uni_session_active(d: date) -> bool:
    """True если в этот период активна университетская сессия."""
    return _in_ranges(d, UNI_SESSION_RANGES)


# ────────────────────────────────────────────────────────────────────
# Сводная функция — все фичи разом
# ────────────────────────────────────────────────────────────────────
def get_seasonal_features(d: date) -> dict[str, Any]:
    """Вернуть dict с 9 сезонными фичами для даты d.

    Returns:
        dict:
            - is_school_break (int 0/1)
            - is_school_start_day (int 0/1)
            - is_mass_vacation (int 0/1)
            - is_pre_holiday (int 0/1)
            - days_to_school_start (int)
            - days_to_new_year (int)
            - is_workday_calendar_rf (int 0/1)
            - uni_session_active (int 0/1)
    """
    return {
        "is_school_break": int(is_school_break(d)),
        "is_school_start_day": int(is_school_start_day(d)),
        "is_mass_vacation": int(is_mass_vacation(d)),
        "is_pre_holiday": int(is_pre_holiday(d)),
        "days_to_school_start": int(days_to_school_start(d)),
        "days_to_new_year": int(days_to_new_year(d)),
        "is_workday_calendar_rf": int(is_workday_calendar_rf(d)),
        "uni_session_active": int(uni_session_active(d)),
    }


__all__ = [
    "HOLIDAYS_2025",
    "MASS_VACATION_RANGES",
    "PRE_HOLIDAY_DAYS",
    "SCHOOL_BREAKS",
    "SCHOOL_START_DAYS",
    "UNI_SESSION_RANGES",
    "WORKDAY_OVERRIDES_2025",
    "days_to_new_year",
    "days_to_school_start",
    "get_seasonal_features",
    "is_mass_vacation",
    "is_pre_holiday",
    "is_school_break",
    "is_school_start_day",
    "is_workday_calendar_rf",
    "uni_session_active",
]
