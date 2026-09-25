"""Tests for per-route / per-hour / per-weekday WAPE diagnose (T-146)."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from transit_ai.reports.diagnose import (
    diagnose,
    per_hour_wape,
    per_route_wape,
    per_weekday_wape,
)


def _make_test_df() -> pd.DataFrame:
    """Тестовый DataFrame: 2 routes × 2 hours × 3 days = 12 строк."""
    dates = pd.date_range("2025-10-01", periods=3, freq="D")
    rows = []
    for d in dates:
        for r in (1, 7):
            for h in (8, 18):
                rows.append(
                    {
                        "timestamp": d + pd.Timedelta(hours=h),
                        "route_id": r,
                        "date": d,
                        "hour": h,
                        "boardings": 100.0 if (r == 1 and h == 8) else 50.0,
                    }
                )
    return pd.DataFrame(rows)


def test_perfect_predictions_give_score_one() -> None:
    df = _make_test_df()
    preds = df["boardings"].values
    out = per_route_wape(df, preds)
    assert all(abs(v - 1.0) < 1e-6 for v in out.values()), out


def test_route_specific_error() -> None:
    """Если только route=1 ошибается на 50%, per_route[1] = 0.5, per_route[7] = 1.0."""
    df = _make_test_df()
    preds = df["boardings"].values.copy()
    # route=1: завышаем на 100% (т.е. ошибка = 100% от истинного)
    mask_route_1 = df["route_id"] == 1
    preds[mask_route_1] = 2 * df.loc[mask_route_1, "boardings"].values
    out = per_route_wape(df, preds)
    # route=1: y=300, |y-ŷ|=300, WAPE=1.0, score=0.0
    assert out[1] == 0.0
    # route=7: y=150, |y-ŷ|=0, WAPE=0, score=1.0
    assert abs(out[7] - 1.0) < 1e-6


def test_per_hour_wape() -> None:
    df = _make_test_df()
    preds = df["boardings"].values.copy()
    mask_hour_8 = df["hour"] == 8
    preds[mask_hour_8] = 2 * df.loc[mask_hour_8, "boardings"].values
    out = per_hour_wape(df, preds)
    # hour=8: все строки завышены в 2x → WAPE=1.0, score=0.0
    assert out[8] == 0.0
    # hour=18: predictions correct → score=1.0
    assert abs(out[18] - 1.0) < 1e-6


def test_per_weekday_wape() -> None:
    df = _make_test_df()
    # Первый день (2025-10-01 = среда = weekday 2) — ошибка 100%
    preds = df["boardings"].values.copy()
    mask_first_day = df["date"] == pd.Timestamp("2025-10-01")
    preds[mask_first_day] = 2 * df.loc[mask_first_day, "boardings"].values
    out = per_weekday_wape(df, preds)
    # weekday=2 (среда): все строки завышены
    assert out[2] == 0.0
    # weekday=3 (четверг): все ОК
    assert abs(out[3] - 1.0) < 1e-6


def test_empty_df_returns_empty_dicts() -> None:
    df = pd.DataFrame(columns=["route_id", "date", "hour", "boardings"])
    preds = np.array([])
    assert per_route_wape(df, preds) == {}
    assert per_hour_wape(df, preds) == {}
    assert per_weekday_wape(df, preds) == {}


def test_diagnose_returns_all_keys() -> None:
    df = _make_test_df()
    preds = df["boardings"].values
    result = diagnose(df, preds)
    assert "overall" in result
    assert "per_route" in result
    assert "per_hour" in result
    assert "per_weekday" in result
    assert "n_points" in result
    assert result["overall"] == pytest.approx(1.0)
    assert result["n_points"] == len(df)


def test_overall_equals_weighted_average() -> None:
    """Overall WAPE-score должен быть Σ_route(score*Σy[route])/Σy.

    Или эквивалентно: 1 - Σ|y-ŷ|/Σy для overall.
    """
    df = _make_test_df()
    preds = df["boardings"].values
    result = diagnose(df, preds)
    assert result["overall"] == pytest.approx(1.0)


def test_real_route_baseline_runs_diagnose() -> None:
    """Integration: проверить diagnose на реальных данных через RouteBaselineMean."""
    from transit_ai.data.base import DateRange
    from transit_ai.data.real import RealSource
    from transit_ai.models.route_baseline import RouteBaselineMean

    src = RealSource()
    train = src.load_ridership(
        DateRange(datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 8, 31, tzinfo=UTC))
    )
    test = src.load_ridership(
        DateRange(datetime(2025, 9, 1, tzinfo=UTC), datetime(2025, 10, 31, tzinfo=UTC))
    )
    model = RouteBaselineMean()
    model.fit(train)
    preds = model.predict_batch(test)
    result = diagnose(test, preds)
    # Ожидаем overall WAPE-score ~0.87 (как раньше замеряли)
    assert 0.80 < result["overall"] < 0.92, f"Got {result['overall']}"
    assert len(result["per_route"]) == 9  # 9 routes в данных (без 5)
    assert len(result["per_hour"]) <= 24
    # Все 9 маршрутов должны быть > 0 (нет cold-start с 0)
    for r, score in result["per_route"].items():
        assert score > 0.5, f"route {r} WAPE-score too low: {score}"
