"""Data source contract (ABC).

Архитектура: см. `.clinerules/01-philosophy.md` (data-agnostic).
Все источники за интерфейсом `DataSource` — замена = 1 файл.

Реализации:
- `SyntheticSource` — генерит правдоподобные данные (T-025)
- `RealSource`     — на хакатоне, читает parquet/csv от организаторов (T-026)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True, slots=True)
class DateRange:
    """Inclusive datetime range for filtering ridership data."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"DateRange start ({self.start}) must be <= end ({self.end})")


class DataSource(ABC):
    """Abstract interface for transit data sources.

    Implementations must return:
    - `load_stops()`: DataFrame with columns [stop_id, name, lat, lon, route_ids]
    - `load_routes()`: DataFrame with columns [route_id, name, stop_ids]
    - `load_ridership(date_range)`: DataFrame with columns
        [timestamp, stop_id, route_id, passenger_count]
    """

    @abstractmethod
    def load_stops(self) -> pd.DataFrame:
        """Load all stops (geometry + names)."""
        raise NotImplementedError

    @abstractmethod
    def load_routes(self) -> pd.DataFrame:
        """Load all routes (sequences of stop_ids)."""
        raise NotImplementedError

    @abstractmethod
    def load_ridership(self, date_range: DateRange) -> pd.DataFrame:
        """Load ridership within [start, end] (inclusive)."""
        raise NotImplementedError

    def validate_schema(self, df: pd.DataFrame, expected: set[str]) -> None:
        """Raise ValueError if required columns are missing. Helper for impls."""
        missing = expected - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")


__all__ = ["DataSource", "DateRange"]
