"""Tests for RealSource — hackathon route-level dataset (T-143).

Validates:
- Schema contract: 5 cols [timestamp, route_id, date, hour, boardings]
- 10 unique routes ∈ {1,5,7,11,12,17,25,26,28,50}
- boardings >= 0, no NaN, hours in {0..23}
- Date range filter works
- load_stops() / load_routes() return expected shapes
- validate() raises on bad data

These tests use the actual data/real/labels/ files. If labels are missing
the test module is skipped (no data, no inference).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource

LABELS_DIR = Path("data/real/labels")

pytestmark = pytest.mark.skipif(
    not (LABELS_DIR / "labels_day_train.csv").exists(),
    reason="Hackathon labels not present (data/real/labels/)",
)


# =====================================================================
# 1. Routes
# =====================================================================


def test_load_routes_returns_10_unique_routes() -> None:
    src = RealSource(labels_dir=LABELS_DIR)
    routes = src.load_routes()
    assert len(routes) == 10
    assert set(routes["route_id"]) == {1, 5, 7, 11, 12, 17, 25, 26, 28, 50}
    assert "name" in routes.columns
    assert all(routes["name"].str.startswith("Трамвай "))


def test_load_stops_returns_empty_or_partial() -> None:
    """Stop-level is optional bonus (F-015). RealSource may return empty."""
    src = RealSource(labels_dir=LABELS_DIR)
    stops = src.load_stops()
    assert isinstance(stops, pd.DataFrame)
    if not stops.empty:
        for col in ("stop_id", "name", "lat", "lon", "route_ids"):
            assert col in stops.columns


# =====================================================================
# 2. load_ridership — schema and shape
# =====================================================================


def test_load_ridership_returns_correct_schema() -> None:
    src = RealSource(labels_dir=LABELS_DIR)
    df = src.load_ridership(DateRange(datetime(2025, 1, 1), datetime(2025, 1, 31)))
    expected = {"timestamp", "route_id", "date", "hour", "boardings"}
    assert expected.issubset(set(df.columns))
    assert df["boardings"].dtype.kind in ("i", "u", "f")
    assert df["hour"].dtype.kind in ("i", "u")


def test_load_ridership_filters_by_date_range() -> None:
    src = RealSource(labels_dir=LABELS_DIR)
    jan = src.load_ridership(DateRange(datetime(2025, 1, 1), datetime(2025, 1, 31)))
    aug = src.load_ridership(DateRange(datetime(2025, 8, 1), datetime(2025, 8, 31)))
    assert (jan["date"] >= "2025-01-01").all() and (jan["date"] <= "2025-01-31").all()
    assert (aug["date"] >= "2025-08-01").all() and (aug["date"] <= "2025-08-31").all()
    assert len(jan) > 0 and len(aug) > 0


def test_load_ridership_route_id_is_int() -> None:
    src = RealSource(labels_dir=LABELS_DIR)
    df = src.load_ridership(DateRange(datetime(2025, 1, 1), datetime(2025, 1, 7)))
    assert df["route_id"].dtype.kind in ("i", "u")
    assert set(df["route_id"].unique()).issubset({1, 5, 7, 11, 12, 17, 25, 26, 28, 50})


def test_load_ridership_timestamp_is_hour_aligned() -> None:
    src = RealSource(labels_dir=LABELS_DIR)
    df = src.load_ridership(DateRange(datetime(2025, 1, 1), datetime(2025, 1, 2)))
    assert (df["timestamp"].dt.hour == df["hour"]).all()
    assert (df["timestamp"].dt.minute == 0).all()
    assert (df["timestamp"].dt.second == 0).all()


# =====================================================================
# 3. validate() — bad data detection
# =====================================================================


def test_validate_raises_on_negative_boardings() -> None:
    bad = pd.DataFrame(
        {
            "route": [25],
            "date": ["2025-01-01"],
            "hour": [8],
            "boardings": [-5],
        }
    )
    with pytest.raises(ValueError, match="[Nn]egative"):
        RealSource.validate(bad)


def test_validate_raises_on_invalid_hour() -> None:
    bad = pd.DataFrame(
        {
            "route": [25],
            "date": ["2025-01-01"],
            "hour": [25],
            "boardings": [10],
        }
    )
    with pytest.raises(ValueError, match="hour"):
        RealSource.validate(bad)


def test_validate_raises_on_missing_columns() -> None:
    bad = pd.DataFrame({"route": [25], "hour": [8]})
    with pytest.raises(ValueError, match="[Mm]issing"):
        RealSource.validate(bad)


def test_validate_raises_on_nan_boardings() -> None:
    bad = pd.DataFrame(
        {
            "route": [25],
            "date": ["2025-01-01"],
            "hour": [8],
            "boardings": [float("nan")],
        }
    )
    with pytest.raises(ValueError, match="[Nn]aN"):
        RealSource.validate(bad)


# =====================================================================
# 4. Sanity checks on real data
# =====================================================================


def test_load_ridership_boardings_non_negative() -> None:
    src = RealSource(labels_dir=LABELS_DIR)
    df = src.load_ridership(DateRange(datetime(2025, 1, 1), datetime(2025, 10, 31)))
    assert (df["boardings"] >= 0).all()


def test_load_ridership_october_subset() -> None:
    """October 2025: ~5500-7500 строк (трамваи ходят не все 24 часа).

    Реальный диапазон может быть любым 0..23 в зависимости от маршрута и даты.
    Главное: данные есть, нет выбросов за пределами 0..23.
    """
    src = RealSource(labels_dir=LABELS_DIR)
    df = src.load_ridership(DateRange(datetime(2025, 10, 1), datetime(2025, 10, 31)))
    # 31 days × 10 routes × ~hours_active ≈ 5500-7500
    assert 5500 < len(df) < 7500, f"Unexpected rows: {len(df)}"
    # Часы строго в [0, 23]
    assert df["hour"].between(0, 23).all(), "Hours out of range"
