"""Tests for weekend multiplier calibration (F-067/T-180-extension, derived from user input).

Идея: реальный weekend трафик в Москве стабильно 60-65% от workday уровня
(train: 0.626, holdout: 0.596 — разница 3pp). Multiplier 0.6 для Sat и 0.5 для Sun
должен поднять holdout WAPE-score на +0.01..0.03.

Применяется ПОСЛЕ per-route bias calibration как layered refinement.
НЕ заменяет bias calibration (T-178 negative, F-068), а дополняет.

Refs: F-067 (negative on structural zeros), user input on holiday/repair schedule.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from transit_ai.calibration.weekend_mult import (
    apply_weekend_mult,
    compute_weekend_mult,
)


def test_compute_weekend_mult_returns_expected_ratios() -> None:
    """Если train data: Saturday mean = 60% от Monday mean → mult_sat = 0.60."""
    df = pd.DataFrame(
        {
            "actual": [1000.0] * 5 + [600.0] * 2,  # 5 workdays + Sat + Sun
            "weekday": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
        }
    )
    mult = compute_weekend_mult(df["actual"], df["weekday"])
    # Monday = 1000, Saturday = 600 → mult_sat = 0.60
    # Но используется agg="median" — для простого теста 1000 vs 600 даст 0.60
    assert mult["Saturday"] == pytest.approx(0.60, abs=0.01), mult
    assert mult["Sunday"] == pytest.approx(0.60, abs=0.01), mult  # тут Sun тоже 600


def test_compute_weekend_mult_different_sat_sun() -> None:
    """Sat=600, Sun=500 → mult_sat=0.60, mult_sun=0.50."""
    df = pd.DataFrame(
        {
            "actual": [1000.0, 600.0, 500.0],
            "weekday": ["Monday", "Saturday", "Sunday"],
        }
    )
    mult = compute_weekend_mult(df["actual"], df["weekday"])
    assert mult["Saturday"] == pytest.approx(0.60, abs=0.01)
    assert mult["Sunday"] == pytest.approx(0.50, abs=0.01)


def test_apply_weekend_mult_scales_predictions() -> None:
    """apply_weekend_mult должен умножить predictions на multiplier по weekday."""
    preds = np.array([1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0])
    weekdays = pd.Series(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    )
    mult = {"Saturday": 0.6, "Sunday": 0.5}
    out = apply_weekend_mult(preds, weekdays, mult)
    expected = np.array([1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 600.0, 500.0])
    np.testing.assert_allclose(out, expected)


def test_apply_weekend_mult_keeps_workday_unchanged() -> None:
    """Mon-Fri НЕ должны изменяться (mult не содержит их)."""
    preds = np.array([1000.0, 1000.0, 1000.0, 1000.0, 1000.0])
    weekdays = pd.Series(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    mult = {"Saturday": 0.6, "Sunday": 0.5}
    out = apply_weekend_mult(preds, weekdays, mult)
    np.testing.assert_allclose(out, preds)  # no change


def test_apply_weekend_mult_immutability() -> None:
    """Входной preds не должен мутироваться."""
    preds = np.array([100.0, 200.0, 300.0])
    weekdays = pd.Series(["Saturday", "Sunday", "Monday"])
    mult = {"Saturday": 0.5, "Sunday": 0.4}
    _ = apply_weekend_mult(preds, weekdays, mult)
    np.testing.assert_array_equal(preds, np.array([100.0, 200.0, 300.0]))


def test_apply_weekend_mult_no_negatives() -> None:
    """Output не должен быть отрицательным (clip к 0)."""
    preds = np.array([1.0, 1.0])
    weekdays = pd.Series(["Saturday", "Sunday"])
    mult = {"Saturday": -0.5, "Sunday": -1.0}  # крайний случай
    out = apply_weekend_mult(preds, weekdays, mult)
    np.testing.assert_array_equal(out, np.array([0.0, 0.0]))


def test_apply_weekend_mult_empty_mult_dict() -> None:
    """Если mult пустой — predictions возвращаются как есть."""
    preds = np.array([100.0, 200.0, 300.0])
    weekdays = pd.Series(["Saturday", "Sunday", "Monday"])
    out = apply_weekend_mult(preds, weekdays, {})
    np.testing.assert_array_equal(out, preds)


def test_compute_weekend_mult_nan_in_actual_raises() -> None:
    """NaN в actual должен raise (или явная обработка), НЕ silently вернуть NaN."""
    df = pd.DataFrame(
        {
            "actual": [1000.0, float("nan"), 600.0],  # NaN в Monday
            "weekday": ["Monday", "Monday", "Saturday"],
        }
    )
    # Текущая реализация даст NaN/NaN = NaN для Saturday mult → corrupted submission
    # Ожидаемое поведение: либо raise, либо skip NaN при вычислении median
    mult = compute_weekend_mult(df["actual"], df["weekday"])
    # Pandas .median() по умолчанию skipna=True → workday_median будет NaN
    # Проверяем что мы НЕ получаем NaN multiplier
    assert "Saturday" in mult
    import math

    assert not math.isnan(mult["Saturday"]), f"Got NaN: {mult}"


def test_apply_weekend_mult_nan_in_preds_no_corruption() -> None:
    """NaN в predictions НЕ должен приводить к NaN в output."""
    preds = np.array([100.0, float("nan"), 100.0])
    weekdays = pd.Series(["Monday", "Saturday", "Sunday"])
    mult = {"Saturday": 0.6, "Sunday": 0.5}
    out = apply_weekend_mult(preds, weekdays, mult)
    # NaN propagates через умножение → NaN в output
    # Должны либо заменить NaN → 0, либо raise
    import math

    # Проверяем что NaN НЕ распространился на всю колонку
    assert not math.isnan(out[0]), "Monday prediction corrupted by NaN propagation"
    assert not math.isnan(out[2]), "Sunday prediction corrupted"


def test_apply_weekend_mult_zero_pred_stays_zero() -> None:
    """Zero prediction × multiplier = zero (не NaN, не отрицательное)."""
    preds = np.array([0.0, 0.0, 100.0])
    weekdays = pd.Series(["Monday", "Saturday", "Sunday"])
    mult = {"Saturday": 0.6, "Sunday": 0.5}
    out = apply_weekend_mult(preds, weekdays, mult)
    np.testing.assert_array_equal(out, np.array([0.0, 0.0, 50.0]))


def test_apply_weekend_mult_only_one_weekday_in_mult() -> None:
    """Если mult содержит только Saturday — Sunday НЕ изменяется."""
    preds = np.array([100.0, 100.0])
    weekdays = pd.Series(["Saturday", "Sunday"])
    mult = {"Saturday": 0.6}  # нет Sunday
    out = apply_weekend_mult(preds, weekdays, mult)
    expected = np.array([60.0, 100.0])  # только Saturday scaled
    np.testing.assert_allclose(out, expected)


def test_compute_weekend_mult_robust_to_outliers() -> None:
    """Median устойчив к outliers (10% данных выбросы НЕ должны сильно влиять)."""
    # Monday: 100 обычных + 1 outlier = 10000
    monday = [100.0] * 99 + [10000.0]
    # Saturday: 60 обычных + 1 outlier = 6000
    saturday = [60.0] * 99 + [6000.0]
    df = pd.DataFrame(
        {
            "actual": monday + saturday,
            "weekday": ["Monday"] * 100 + ["Saturday"] * 100,
        }
    )
    mult = compute_weekend_mult(df["actual"], df["weekday"])
    # median устойчив: Monday median ~100, Saturday median ~60 → mult ~0.60
    assert mult["Saturday"] == pytest.approx(0.60, abs=0.05), f"mult={mult}"


def test_apply_weekend_mult_preserves_input_type_float64() -> None:
    """Output dtype должен быть float64 (не int если input был int)."""
    preds = np.array([100, 200, 300])  # int
    weekdays = pd.Series(["Monday", "Saturday", "Sunday"])
    mult = {"Saturday": 0.5, "Sunday": 0.5}
    out = apply_weekend_mult(preds, weekdays, mult)
    assert out.dtype == np.float64, f"Got dtype {out.dtype}"


def test_apply_weekend_mult_mult_greater_than_one() -> None:
    """Mult > 1 (если weekend > workday, что не должно быть) → корректно умножает."""
    preds = np.array([100.0, 100.0])
    weekdays = pd.Series(["Saturday", "Sunday"])
    mult = {"Saturday": 1.5, "Sunday": 1.2}
    out = apply_weekend_mult(preds, weekdays, mult)
    expected = np.array([150.0, 120.0])
    np.testing.assert_allclose(out, expected)


def test_apply_weekend_mult_input_dataframe_weekday_column() -> None:
    """Если weekday — pd.Series с другим индексом, должно работать (не по позиции)."""
    preds = np.array([100.0, 200.0, 300.0])
    # Series с НЕ-стандартным индексом
    weekdays = pd.Series(["Monday", "Saturday", "Sunday"], index=[10, 20, 30])
    mult = {"Saturday": 0.5, "Sunday": 0.5}
    out = apply_weekend_mult(preds, weekdays, mult)
    # ОЖИДАНИЕ: работает по позиции (массив), не по индексу
    # Если по индексу — будет KeyError или пустой результат
    expected = np.array([100.0, 100.0, 150.0])
    np.testing.assert_allclose(out, expected)
