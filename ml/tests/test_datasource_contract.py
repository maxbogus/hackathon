"""Tests for ml.transit_ai.data.base.DataSource contract."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from transit_ai.data.base import DataSource, DateRange


class _FakeSource(DataSource):
    """Minimal DataSource impl used only to test the abstract contract."""

    def load_stops(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "stop_id": [1, 2],
                "name": ["A", "B"],
                "lat": [55.0, 55.1],
                "lon": [37.0, 37.1],
            }
        )

    def load_routes(self) -> pd.DataFrame:
        return pd.DataFrame({"route_id": [10], "stop_ids": [[1, 2]]})

    def load_ridership(self, date_range: DateRange) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "timestamp": pd.date_range(date_range.start, periods=2, freq="h"),
                "stop_id": [1, 2],
                "route_id": [10, 10],
                "passenger_count": [5, 7],
            }
        )


def test_datasource_is_abstract() -> None:
    """Cannot instantiate DataSource directly — it's an ABC."""
    with pytest.raises(TypeError):
        DataSource()  # type: ignore[abstract]


def test_fake_source_implements_contract() -> None:
    src = _FakeSource()
    assert isinstance(src, DataSource)
    assert not src.load_stops().empty
    assert not src.load_routes().empty


def test_daterange_must_be_valid() -> None:
    with pytest.raises(ValueError):
        DateRange(start=datetime(2026, 1, 2), end=datetime(2026, 1, 1))


def test_daterange_accepts_equal_bounds() -> None:
    dr = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 1))
    assert dr.start == dr.end


def test_validate_schema_helper() -> None:
    src = _FakeSource()
    df = pd.DataFrame({"a": [1], "b": [2]})
    src.validate_schema(df, expected={"a", "b"})  # no error

    with pytest.raises(ValueError, match="missing required columns"):
        src.validate_schema(df, expected={"a", "c"})
