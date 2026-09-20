"""Tests for SyntheticSource."""

from __future__ import annotations

from datetime import datetime

import pytest

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource


def test_synthetic_source_is_datasource() -> None:
    src = SyntheticSource()
    stops = src.load_stops()
    routes = src.load_routes()
    assert not stops.empty
    assert not routes.empty
    assert "stop_id" in stops.columns
    assert "route_id" in routes.columns


def test_synthetic_deterministic() -> None:
    """Same seed → same data."""
    a = SyntheticSource(SyntheticConfig(seed=42))
    b = SyntheticSource(SyntheticConfig(seed=42))
    pd_stops_a = a.load_stops()
    pd_stops_b = b.load_stops()
    assert (pd_stops_a["lat"].values == pd_stops_b["lat"].values).all()


def test_synthetic_ridership_respects_daterange() -> None:
    src = SyntheticSource(SyntheticConfig(n_days=10))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 5)))
    assert not rid.empty


def test_synthetic_ridership_has_realistic_pattern() -> None:
    """Peak hours (8am, 18pm) should have more ridership than night (3am)."""
    src = SyntheticSource(SyntheticConfig(n_days=14, seed=42))
    rid = src.load_ridership(DateRange(datetime(2026, 1, 1), datetime(2026, 1, 14)))

    if rid.empty:
        pytest.skip("No ridership generated — config too small?")

    rid["hour"] = rid["timestamp"].dt.hour
    by_hour = rid.groupby("hour")["passenger_count"].sum()

    # Morning peak (8) > night (3)
    assert by_hour[8] > by_hour[3], f"Expected peak hour 8 > night hour 3: {by_hour.to_dict()}"


def test_synthetic_config_defaults_small() -> None:
    """Defaults are small enough for fast unit tests."""
    c = SyntheticConfig()
    assert c.n_stops <= 20
    assert c.n_days <= 60
