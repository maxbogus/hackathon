"""Schedule overrides (T-180-extension v2, derived from F-073 user data).

Применяются ТОЛЬКО к submission period (ноя-дек 2025), UNTESTABLE на holdout.
Использовать ОСТОРОЖНО — каждое override требует слот на платформу для проверки.

Refs: F-073 user input on Nov-Dec 2025 tram schedule changes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "apply_evening_shortened",
    "apply_event_multiplier",
    "apply_holiday_override",
    "apply_partial_zero",
    "apply_period_multiplier",
    "apply_vacation_multiplier",
]


def apply_partial_zero(
    predictions: np.ndarray,
    route: pd.Series,
    date: pd.Series,
    route_id: int,
    zero_dates: pd.DatetimeIndex | pd.Series,
) -> np.ndarray:
    """Занулить predictions для конкретного route_id на конкретные даты.

    Use case: route 5 не работал до 16 декабря → занулить только этот период,
    оставить boardings для 16-31 декабря (если трамвай реально работал).

    Args:
        predictions: массив predictions (уже bias-calibrated, weekend-mult'ed).
        route: pandas Series с route_id для каждого row.
        date: pandas Series с датами для каждого row.
        route_id: какой маршрут занулять.
        zero_dates: даты (DatetimeIndex или Series) для зануления.

    Returns:
        Новый массив с занулёнными (route_id, date) комбинациями.
        Входной predictions не мутируется.

    Edge cases:
        - zero_dates пустой → predictions как есть.
        - route_id не в данных → no-op.
        - date не в zero_dates → no-op.
    """
    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()

    if len(zero_dates) == 0:
        return out

    zero_set = set(pd.to_datetime(zero_dates).normalize())
    date_arr = pd.to_datetime(date).dt.normalize().values
    route_arr = np.asarray(route.values, dtype=int)

    mask = np.isin(date_arr, list(zero_set)) & (route_arr == int(route_id))
    out[mask] = 0.0

    return out


def apply_evening_shortened(
    predictions: np.ndarray,
    route: pd.Series,
    date: pd.Series,
    hour: pd.Series,
    routes: list[int],
    min_hour: int,
    dates: pd.DatetimeIndex | pd.Series,
    multiplier: float,
) -> np.ndarray:
    """Применить multiplier к (route ∈ routes, hour >= min_hour, date ∈ dates).

    Use case: route 7, 50 укорочены после 22:00 в ноя-дек → меньше трафика.
    multiplier < 1.0 уменьшает predictions; multiplier=0.0 занулит.

    Args:
        predictions: массив predictions.
        route: pandas Series с route_id.
        date: pandas Series с датами.
        hour: pandas Series с часами (0-23).
        routes: список route_id для применения.
        min_hour: минимальный час (включительно) для применения.
        dates: даты для применения.
        multiplier: множитель (0.0 = zero, 1.0 = no change).

    Returns:
        Новый массив с scaled predictions (>= 0). Не мутирует input.
    """
    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()

    if len(dates) == 0 or not routes:
        return out

    date_set = set(pd.to_datetime(dates).normalize())
    date_arr = pd.to_datetime(date).dt.normalize().values
    route_arr = np.asarray(route.values, dtype=int)
    hour_arr = np.asarray(hour.values, dtype=int)

    routes_set = {int(r) for r in routes}
    mask = (
        np.isin(date_arr, list(date_set))
        & np.isin(route_arr, list(routes_set))
        & (hour_arr >= int(min_hour))
    )

    if mask.any():
        out[mask] = preds[mask] * float(multiplier)

    return np.maximum(out, 0.0)


def apply_holiday_override(
    predictions: np.ndarray,
    route: pd.Series,
    dates: pd.Series,
    target_date: pd.Timestamp,
    multiplier: float = 0.0,
) -> np.ndarray:
    """Применить multiplier ко ВСЕМ маршрутам на конкретную дату (holiday override).

    Use case: 3 ноября = перенос выходного (государственный выходной, как 4 ноября).
    multiplier=0.0 занулит весь день (risk: real traffic != 0).
    multiplier=0.5 уменьшит вдвое (если weekend-уровень трафика).

    Args:
        predictions: массив predictions.
        route: pandas Series с route_id.
        date: pandas Series с датами.
        date: конкретная дата для override.
        multiplier: множитель (default 0.0 = zero весь день).

    Returns:
        Новый массив с scaled predictions (>= 0). Не мутирует input.
    """
    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()

    target_date = pd.Timestamp(target_date).normalize()
    date_arr = pd.to_datetime(dates).dt.normalize().values

    mask = date_arr == target_date
    if mask.any():
        out[mask] = preds[mask] * float(multiplier)

    return np.maximum(out, 0.0)


def apply_period_multiplier(
    predictions: np.ndarray,
    route: pd.Series,
    date: pd.Series,
    hour: pd.Series,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    multiplier: float,
    routes: list[int] | None = None,
    hours: list[int] | None = None,
) -> np.ndarray:
    """Apply multiplier к date range (для cold snap, multi-day events).

    Args:
        predictions: массив predictions.
        route: pandas Series с route_id.
        date: pandas Series с датами.
        hour: pandas Series с часами.
        start_date: начало диапазона (inclusive).
        end_date: конец диапазона (inclusive).
        multiplier: множитель (0.92 = -8%, 1.10 = +10%).
        routes: опциональный список route_id для фильтрации.
        hours: опциональный список часов для фильтрации.

    Returns:
        Новый массив с scaled predictions (>= 0).
    """
    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    date_arr = pd.to_datetime(date)
    route_arr = np.asarray(route.values, dtype=int)
    hour_arr = np.asarray(hour.values, dtype=int)

    date_mask = (date_arr >= start) & (date_arr <= end)
    if routes is not None:
        route_mask = np.isin(route_arr, [int(r) for r in routes])
    else:
        route_mask = np.ones(len(preds), dtype=bool)
    if hours is not None:
        hour_mask = np.isin(hour_arr, [int(h) for h in hours])
    else:
        hour_mask = np.ones(len(preds), dtype=bool)

    mask = date_mask & route_mask & hour_mask
    if mask.any():
        out[mask] = preds[mask] * float(multiplier)

    return np.maximum(out, 0.0)


def apply_event_multiplier(
    predictions: np.ndarray,
    route: pd.Series,
    date: pd.Series,
    hour: pd.Series,
    route_id: int,
    multiplier: float,
    event_date: pd.Timestamp | None = None,
    start_date: pd.Timestamp | None = None,
    end_date: pd.Timestamp | None = None,
    start_hour: int | None = None,
    end_hour: int | None = None,
) -> np.ndarray:
    """Apply multiplier для конкретного route_id на дату/диапазон дат и часов.

    Args:
        predictions: массив predictions.
        route: pandas Series с route_id.
        date: pandas Series с датами.
        hour: pandas Series с часами.
        route_id: какой маршрут scaled.
        multiplier: множитель.
        event_date: дата события (single date mode).
        start_date: начало диапазона (multi-day mode, mutually exclusive с event_date).
        end_date: конец диапазона (multi-day mode).
        start_hour: начальный час (опционально, None = весь день).
        end_hour: конечный час (опционально).

    Returns:
        Новый массив с scaled predictions (>= 0).
    """
    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()

    if event_date is not None and start_date is None and end_date is None:
        start = pd.Timestamp(event_date)
        end = pd.Timestamp(event_date)
    elif start_date is not None and end_date is not None:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
    else:
        return out  # invalid args

    date_arr = pd.to_datetime(date)
    route_arr = np.asarray(route.values, dtype=int)
    hour_arr = np.asarray(hour.values, dtype=int)

    mask = (date_arr >= start) & (date_arr <= end) & (route_arr == int(route_id))
    if start_hour is not None and end_hour is not None:
        mask = mask & (hour_arr >= int(start_hour)) & (hour_arr <= int(end_hour))

    if mask.any():
        out[mask] = preds[mask] * float(multiplier)

    return np.maximum(out, 0.0)


def apply_vacation_multiplier(
    predictions: np.ndarray,
    route: pd.Series,
    date: pd.Series,
    hour: pd.Series,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    school_hours: list[int],
    multiplier: float,
    routes: list[int] | None = None,
) -> np.ndarray:
    """Apply multiplier для школьных часов во время каникул.

    Args:
        predictions: массив predictions.
        route: pandas Series с route_id.
        date: pandas Series с датами.
        hour: pandas Series с часами.
        start_date: начало каникул.
        end_date: конец каникул.
        school_hours: часы школьного трафика (обычно 6-9 утра, 13-16 дня).
        multiplier: множитель (0.85 = -15% school traffic).
        routes: опциональный фильтр по маршрутам.

    Returns:
        Новый массив с scaled predictions (>= 0).
    """
    return apply_period_multiplier(
        predictions=predictions,
        route=route,
        date=date,
        hour=hour,
        start_date=start_date,
        end_date=end_date,
        multiplier=multiplier,
        routes=routes,
        hours=school_hours,
    )
