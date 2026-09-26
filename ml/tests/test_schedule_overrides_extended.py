"""Tests for extended schedule overrides (Phase 2: events, vacations, cold snap)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from transit_ai.calibration.schedule_overrides import (
    apply_event_multiplier,
    apply_period_multiplier,
    apply_vacation_multiplier,
)


def test_apply_period_multiplier_scales_date_range() -> None:
    """Period multiplier должен применить multiplier ко ВСЕМ датам в диапазоне."""
    df = pd.DataFrame(
        {
            "route": [1, 1, 1, 1, 1],
            "date": pd.to_datetime(
                ["2025-12-22", "2025-12-23", "2025-12-25", "2025-12-31", "2026-01-01"]
            ),
            "hour": [12, 12, 12, 12, 12],
        }
    )
    preds = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
    out = apply_period_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        start_date=pd.Timestamp("2025-12-23"),
        end_date=pd.Timestamp("2025-12-31"),
        multiplier=0.92,
    )
    # 23, 25, 31 декабря scaled ×0.92; 22 декабря и 1 января без изменений
    expected = np.array([100.0, 92.0, 92.0, 92.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_period_multiplier_specific_routes() -> None:
    """Period multiplier для конкретных routes, остальные без изменений."""
    df = pd.DataFrame(
        {
            "route": [1, 7, 50, 25],
            "date": pd.to_datetime(
                ["2025-12-25", "2025-12-25", "2025-12-25", "2025-12-25"]
            ),
        }
    )
    preds = np.array([100.0, 200.0, 300.0, 400.0])
    out = apply_period_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"] if "hour" in df.columns else pd.Series([12] * 4),
        start_date=pd.Timestamp("2025-12-25"),
        end_date=pd.Timestamp("2025-12-31"),
        multiplier=0.95,
        routes=[7, 50],
    )
    expected = np.array([100.0, 190.0, 285.0, 400.0])  # route 1 и 25 без изменений
    np.testing.assert_allclose(out, expected)


def test_apply_period_multiplier_specific_hours() -> None:
    """Period multiplier для конкретных hours (утренний час пик)."""
    df = pd.DataFrame(
        {
            "route": [1, 1, 1, 1],
            "date": pd.to_datetime(
                ["2025-12-25", "2025-12-25", "2025-12-25", "2025-12-25"]
            ),
            "hour": [5, 7, 9, 12],
        }
    )
    preds = np.array([100.0, 100.0, 100.0, 100.0])
    out = apply_period_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        start_date=pd.Timestamp("2025-12-25"),
        end_date=pd.Timestamp("2025-12-31"),
        multiplier=0.9,
        hours=[6, 7, 8, 9],
    )
    # hour=7 и hour=9 scaled; hour=5 и hour=12 без изменений
    expected = np.array([100.0, 90.0, 90.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_event_multiplier_specific_route_date_hour() -> None:
    """Event multiplier: route × date × (час) × multiplier."""
    df = pd.DataFrame(
        {
            "route": [7, 7, 7, 50],
            "date": pd.to_datetime(
                ["2025-11-22", "2025-11-22", "2025-11-22", "2025-11-22"]
            ),
            "hour": [16, 18, 22, 18],
        }
    )
    preds = np.array([100.0, 100.0, 100.0, 100.0])
    out = apply_event_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        route_id=7,
        event_date=pd.Timestamp("2025-11-22"),
        start_hour=15,
        end_hour=20,
        multiplier=1.10,
    )
    # route 7 hours 16, 18 (внутри 15-20) scaled ×1.10
    expected = np.array([110.0, 110.0, 100.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_event_multiplier_daily_no_hours() -> None:
    """Event multiplier без hour filter = весь день."""
    df = pd.DataFrame(
        {
            "route": [17, 17, 17],
            "date": pd.to_datetime(["2025-12-25", "2025-12-25", "2025-12-25"]),
            "hour": [10, 14, 20],
        }
    )
    preds = np.array([100.0, 100.0, 100.0])
    out = apply_event_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        route_id=17,
        event_date=pd.Timestamp("2025-12-25"),
        start_hour=None,  # весь день
        end_hour=None,
        multiplier=1.15,
    )
    expected = np.array([115.0, 115.0, 115.0])
    np.testing.assert_allclose(out, expected)


def test_apply_event_multiplier_multi_day() -> None:
    """Event multiplier multi-day: ярмарка с 25 декабря по 31 декабря."""
    df = pd.DataFrame(
        {
            "route": [17, 17, 17, 17],
            "date": pd.to_datetime(
                ["2025-12-24", "2025-12-25", "2025-12-31", "2026-01-01"]
            ),
        }
    )
    preds = np.array([100.0, 100.0, 100.0, 100.0])
    out = apply_event_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"] if "hour" in df.columns else pd.Series([12] * 4),
        route_id=17,
        start_date=pd.Timestamp("2025-12-25"),
        end_date=pd.Timestamp("2025-12-31"),
        multiplier=1.15,
    )
    # 25 и 31 декабря scaled; 24 декабря и 1 января без изменений
    expected = np.array([100.0, 115.0, 115.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_vacation_multiplier_school_hours() -> None:
    """Vacation multiplier: school hours (h6-9) во время каникул."""
    df = pd.DataFrame(
        {
            "route": [1, 1, 1, 1],
            "date": pd.to_datetime(
                ["2025-11-01", "2025-11-01", "2025-11-01", "2025-11-01"]
            ),
            "hour": [6, 8, 14, 20],
        }
    )
    preds = np.array([100.0, 100.0, 100.0, 100.0])
    out = apply_vacation_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        start_date=pd.Timestamp("2025-11-01"),
        end_date=pd.Timestamp("2025-11-04"),
        school_hours=[6, 7, 8, 9],
        multiplier=0.85,
    )
    # h6, h8 scaled ×0.85; h14, h20 без изменений
    expected = np.array([85.0, 85.0, 100.0, 100.0])
    np.testing.assert_allclose(out, expected)


def test_apply_period_multiplier_no_dates_in_range() -> None:
    """Если ни одна дата в диапазоне — predictions без изменений."""
    df = pd.DataFrame(
        {
            "route": [1, 1],
            "date": pd.to_datetime(["2025-11-01", "2025-11-02"]),
            "hour": [12, 12],
        }
    )
    preds = np.array([100.0, 100.0])
    out = apply_period_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        start_date=pd.Timestamp("2025-12-23"),
        end_date=pd.Timestamp("2025-12-31"),
        multiplier=0.5,
    )
    np.testing.assert_array_equal(out, preds)


def test_apply_event_multiplier_no_match() -> None:
    """Если route_id не совпадает — predictions без изменений."""
    df = pd.DataFrame(
        {
            "route": [1, 1],
            "date": pd.to_datetime(["2025-11-22", "2025-11-22"]),
            "hour": [18, 18],
        }
    )
    preds = np.array([100.0, 100.0])
    out = apply_event_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        route_id=7,  # route 7, не route 1
        event_date=pd.Timestamp("2025-11-22"),
        start_hour=15,
        end_hour=20,
        multiplier=2.0,
    )
    np.testing.assert_array_equal(out, preds)


def test_apply_period_multiplier_immutability() -> None:
    """Входной preds не должен мутироваться."""
    df = pd.DataFrame(
        {
            "route": [1],
            "date": pd.to_datetime(["2025-12-25"]),
            "hour": [12],
        }
    )
    preds = np.array([100.0])
    _ = apply_period_multiplier(
        preds,
        df["route"],
        df["date"],
        df["hour"],
        start_date=pd.Timestamp("2025-12-25"),
        end_date=pd.Timestamp("2025-12-25"),
        multiplier=0.5,
    )
    assert preds[0] == 100.0
