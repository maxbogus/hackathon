"""Weekend multiplier calibration (T-180-extension).

Идея: реальный weekend трафик в Москве стабильно 60-65% от workday уровня
(train: 0.626, holdout: 0.596 — разница 3pp). Multiplier 0.6 для Sat и 0.5 для Sun
должен поднять holdout WAPE-score на +0.01..0.03.

Применяется ПОСЛЕ per-route bias calibration как layered refinement.
НЕ заменяет bias calibration (T-178 negative, F-068), а дополняет.

Refs: user input 2026-09-26 on holiday/repair schedule for Nov-Dec 2025.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["apply_weekend_mult", "compute_weekend_mult"]


def compute_weekend_mult(
    train_actual: pd.Series,
    weekday: pd.Series,
    workday_anchor: str = "Monday",
) -> dict[str, float]:
    """Вычислить multiplier = median(actual_weekend) / median(actual_workday).

    Args:
        train_actual: фактические boardings (для вычисления ratio).
        weekday: pandas Series с weekday (Monday, Tuesday, ..., Sunday).
        workday_anchor: какой workday использовать как reference (default Monday).

    Returns:
        {"Saturday": mult_sat, "Sunday": mult_sun}. Workdays не в dict.

    Raises:
        ValueError: если входные данные пустые или workday_anchor отсутствует.
    """
    if len(train_actual) == 0 or len(weekday) == 0:
        raise ValueError(
            f"Cannot compute weekend mult on empty data "
            f"(len actual={len(train_actual)}, weekday={len(weekday)})"
        )

    df = pd.DataFrame(
        {
            "actual": train_actual.values,
            "weekday": weekday.values,
        }
    )

    # Workday reference = median по workday_anchor (default Monday)
    workday_values = df.loc[df["weekday"] == workday_anchor, "actual"]
    if len(workday_values) == 0:
        raise ValueError(
            f"workday_anchor={workday_anchor!r} not found in data. "
            f"Available weekdays: {sorted(df['weekday'].unique())}"
        )
    workday_median = float(workday_values.median())
    if workday_median <= 0:
        raise ValueError(f"workday_median={workday_median} must be > 0")

    mult: dict[str, float] = {}
    for day_name in ["Saturday", "Sunday"]:
        day_values = df.loc[df["weekday"] == day_name, "actual"]
        if len(day_values) == 0:
            # Нет данных для этого дня — пропускаем (mult=1.0 = no change)
            continue
        day_median = float(day_values.median())
        mult[day_name] = day_median / workday_median

    return mult


def apply_weekend_mult(
    predictions: np.ndarray,
    weekday: pd.Series,
    mult: dict[str, float],
) -> np.ndarray:
    """Применить weekend multiplier к predictions.

    Args:
        predictions: исходные predictions (уже bias-calibrated).
        weekday: pandas Series с weekday для каждого prediction.
        mult: {"Saturday": mult_sat, "Sunday": mult_sun} из compute_weekend_mult.

    Returns:
        Новый массив scaled predictions (>= 0). Входной массив не мутируется.
        Workdays (Mon-Fri) НЕ изменяются. Days без записи в mult — no change.

    Edge cases:
        - Пустой mult → возвращает predictions как есть.
        - mult отрицательный → output 0 (clip).
        - weekday не str → ValueError через Series construction.
    """
    if len(predictions) == 0:
        return predictions.copy()

    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()  # defensive copy

    if not mult:
        return out  # no change

    weekday_arr = np.asarray(weekday.values)
    for day_name, day_mult in mult.items():
        mask = weekday_arr == day_name
        if mask.any():
            out[mask] = preds[mask] * float(day_mult)

    return np.maximum(out, 0.0)  # не уходим в отрицательные
