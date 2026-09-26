"""Tests for schedule overrides (F-073/T-180-extension v2).

Из user data (ноя-дек 2025):
- Route 5 не работал до 16 декабря (cold start, открыт 16.12)
- Route 7, 50 укорочены после 22:00 (весь ноя-дек)
- 3 ноября = перенос выходного (holiday override)

Все overrides UNTESTABLE на holdout (сен-окт 2025), нужны для слота на платформу.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from transit_ai.calibration.schedule_overrides import (
    apply_evening_shortened,
    apply_holiday_override,
    apply_partial_zero,
)


def test_apply_partial_zero_zeros_specific_dates() -> None:
    """partial_zero должен занулить route_id только на указанные даты."""
    df = pd.DataFrame(
        {
            "route": [5, 5, 5, 5, 5, 5],
            "date": pd.to_datetime(
                [
                    "2025-12-01",
                    "2025-12-15",
                    "2025-12-16",
                    "2025-12-20",
                    "2025-12-31",
                    "2025-11-15",
                ]
            ),
        }
    )
    pred = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    zero_dates = pd.to_datetime(["2025-12-01", "2025-12-15", "2025-11-15"])
    out = apply_partial_zero(
        pred, df["route"], df["date"], route_id=5, zero_dates=zero_dates
    )
    expected = np.array([0.0, 0.0, 100.0, 100.0, 100.0, 0.0])
    np.testing.assert_array_equal(out, expected)


def test_apply_partial_zero_other_routes_unchanged() -> None:
    """partial_zero для route=5 НЕ должен трогать другие маршруты."""
    df = pd.DataFrame(
        {
            "route": [5, 7, 5, 50, 7],
            "date": pd.to_datetime(
                ["2025-12-01", "2025-12-01", "2025-12-02", "2025-12-01", "2025-12-02"]
            ),
        }
    )
    pred = np.array([100.0, 200.0, 100.0, 300.0, 200.0])
    zero_dates = pd.to_datetime(["2025-12-01"])
    out = apply_partial_zero(
        pred, df["route"], df["date"], route_id=5, zero_dates=zero_dates
    )
    expected = np.array(
        [0.0, 200.0, 100.0, 300.0, 200.0]
    )  # только route 5 на 12-01 занулён
    np.testing.assert_array_equal(out, expected)


def test_apply_evening_shortened_scales_specific_hours() -> None:
    """evening_shortened должен применить multiplier к (route, hour>=22) на конкретные даты."""
    df = pd.DataFrame(
        {
            "route": [7, 7, 7, 50, 7],
            "date": pd.to_datetime(
                ["2025-11-15", "2025-11-15", "2025-11-15", "2025-11-15", "2025-12-01"]
            ),
            "hour": [21, 22, 23, 23, 22],
        }
    )
    pred = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
    out = apply_evening_shortened(
        pred,
        df["route"],
        df["date"],
        df["hour"],
        routes=[7, 50],
        min_hour=22,
        dates=pd.to_datetime(["2025-11-15"]),
        multiplier=0.5,
    )
    expected = np.array([100.0, 50.0, 50.0, 50.0, 100.0])  # только 22+ на 11.15
    np.testing.assert_allclose(out, expected)


def test_apply_evening_shortened_other_dates_unchanged() -> None:
    """evening_shortened на 11.15 НЕ должен трогать 12.01."""
    df = pd.DataFrame(
        {
            "route": [7, 7],
            "date": pd.to_datetime(["2025-11-15", "2025-12-01"]),
            "hour": [23, 23],
        }
    )
    pred = np.array([100.0, 100.0])
    out = apply_evening_shortened(
        pred,
        df["route"],
        df["date"],
        df["hour"],
        routes=[7],
        min_hour=22,
        dates=pd.to_datetime(["2025-11-15"]),
        multiplier=0.5,
    )
    expected = np.array([50.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_holiday_override_zeros_entire_day() -> None:
    """holiday_override должен занулить все маршруты на конкретную дату (или применить mult)."""
    df = pd.DataFrame(
        {
            "route": [1, 7, 50],
            "date": pd.to_datetime(["2025-11-03", "2025-11-03", "2025-11-03"]),
        }
    )
    pred = np.array([100.0, 200.0, 300.0])
    out = apply_holiday_override(
        pred,
        df["route"],
        df["date"],
        target_date=pd.Timestamp("2025-11-03"),
        multiplier=0.0,
    )
    expected = np.array([0.0, 0.0, 0.0])
    np.testing.assert_array_equal(out, expected)


def test_apply_holiday_override_partial_multiplier() -> None:
    """holiday_override с mult=0.5 (если трафик есть, но снижен)."""
    df = pd.DataFrame(
        {
            "route": [1, 7],
            "date": pd.to_datetime(["2025-11-03", "2025-11-04"]),
        }
    )
    pred = np.array([100.0, 100.0])
    out = apply_holiday_override(
        pred,
        df["route"],
        df["date"],
        target_date=pd.Timestamp("2025-11-03"),
        multiplier=0.5,
    )
    expected = np.array([50.0, 100.0])  # только 11.03
    np.testing.assert_allclose(out, expected)


def test_apply_evening_shortened_other_routes_unchanged() -> None:
    """evening_shortened для route 7/50 НЕ должен трогать route 1."""
    df = pd.DataFrame(
        {
            "route": [1, 7, 50, 11],
            "date": pd.to_datetime(
                ["2025-11-15", "2025-11-15", "2025-11-15", "2025-11-15"]
            ),
            "hour": [23, 23, 23, 23],
        }
    )
    pred = np.array([100.0, 100.0, 100.0, 100.0])
    out = apply_evening_shortened(
        pred,
        df["route"],
        df["date"],
        df["hour"],
        routes=[7, 50],
        min_hour=22,
        dates=pd.to_datetime(["2025-11-15"]),
        multiplier=0.5,
    )
    expected = np.array([100.0, 50.0, 50.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_partial_zero_empty_zero_dates() -> None:
    """Если zero_dates пустой — pred возвращается как есть."""
    df = pd.DataFrame(
        {
            "route": [5, 5],
            "date": pd.to_datetime(["2025-12-01", "2025-12-02"]),
        }
    )
    pred = np.array([100.0, 100.0])
    out = apply_partial_zero(
        pred, df["route"], df["date"], route_id=5, zero_dates=pd.to_datetime([])
    )
    np.testing.assert_array_equal(out, pred)


def test_apply_evening_shortened_immutability() -> None:
    """Входной pred не должен мутироваться."""
    df = pd.DataFrame(
        {
            "route": [7],
            "date": pd.to_datetime(["2025-11-15"]),
            "hour": [23],
        }
    )
    pred = np.array([100.0])
    _ = apply_evening_shortened(
        pred,
        df["route"],
        df["date"],
        df["hour"],
        routes=[7],
        min_hour=22,
        dates=pd.to_datetime(["2025-11-15"]),
        multiplier=0.5,
    )
    np.testing.assert_array_equal(pred, np.array([100.0]))


def test_apply_holiday_override_clip_negative() -> None:
    """Если multiplier отрицательный → clip to 0."""
    df = pd.DataFrame(
        {
            "route": [1],
            "date": pd.to_datetime(["2025-11-03"]),
        }
    )
    pred = np.array([100.0])
    out = apply_holiday_override(
        pred,
        df["route"],
        df["date"],
        target_date=pd.Timestamp("2025-11-03"),
        multiplier=-0.5,
    )
    np.testing.assert_array_equal(out, np.array([0.0]))
