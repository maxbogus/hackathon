"""Synthetic data source for development and tests.

Генерит правдоподобные данные остановок, маршрутов и ridership с реалистичными
паттернами (утренний/вечерний пик, спад в выходные).

Архитектура: см. `.clinerules/01-philosophy.md` (data-agnostic, MVP first).
- `SyntheticSource` — для разработки и тестов, НЕ для production (R5 hackathon-rules).
- Полная синтетика (800 stops × 40 routes × 2 years) — в `gen_synthetic.py` script.
- Дефолтная конфигурация (для тестов): 10 stops × 5 routes × 30 days = маленькая, deterministic.

Real data на хакатоне: `RealSource` (T-026), читает parquet от организаторов.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from transit_ai.data.base import DataSource, DateRange


@dataclass
class SyntheticConfig:
    """Параметры синтетического генератора.

    Defaults выбраны маленькими для быстрых unit-тестов.
    Production-размеры — в `ml/scripts/gen_synthetic.py`.
    """

    n_stops: int = 10
    n_routes: int = 5
    n_days: int = 30
    seed: int = 42
    epoch_date: str = "2026-01-01"  # первый день синтетики

    # Москва bbox
    lat_min: float = 55.55
    lat_max: float = 55.92
    lon_min: float = 37.30
    lon_max: float = 37.85

    # Per-stop ridership: mu ~ Uniform(min, max), sigma ~ mu * 0.2
    ridership_min: float = 10.0
    ridership_max: float = 100.0

    # Peak hour multipliers (утро/вечер в будни, меньше в выходные)
    peak_morning: tuple[int, ...] = (7, 8, 9, 10)
    peak_evening: tuple[int, ...] = (17, 18, 19, 20)
    peak_mult: float = 1.8
    weekend_mult: float = 0.6
    night_mult: float = 0.2  # 0-6 утра


class SyntheticSource(DataSource):
    """Synthetic transit data with realistic ridership patterns."""

    def __init__(self, config: SyntheticConfig | None = None) -> None:
        self.config = config or SyntheticConfig()
        self._rng = np.random.default_rng(self.config.seed)

    # ---- Geometry ----

    def load_stops(self) -> pd.DataFrame:
        c = self.config
        n = c.n_stops
        lats = self._rng.uniform(c.lat_min, c.lat_max, n)
        lons = self._rng.uniform(c.lon_min, c.lon_max, n)
        # ~10% stops — hubs (выше ridership baseline)
        is_hub = self._rng.random(n) < 0.1

        stops = pd.DataFrame(
            {
                "stop_id": np.arange(1, n + 1, dtype=np.int64),
                "name": [f"Stop-{i + 1}" for i in range(n)],
                "lat": lats,
                "lon": lons,
                "is_hub": is_hub,
            }
        )
        return stops

    def load_routes(self) -> pd.DataFrame:
        c = self.config
        routes = []
        for r in range(1, c.n_routes + 1):
            n_stops_in_route = int(self._rng.integers(3, min(8, c.n_stops) + 1))
            stop_ids = sorted(self._rng.choice(c.n_stops, size=n_stops_in_route, replace=False).tolist())
            routes.append({"route_id": r, "name": f"Route-{r}", "stop_ids": stop_ids})
        return pd.DataFrame(routes)

    def load_ridership(self, date_range: DateRange) -> pd.DataFrame:
        c = self.config
        stops_df = self.load_stops()
        routes_df = self.load_routes()

        # Synthetic horizon: days 0..(n_days-1) relative to a fixed epoch.
        # Default epoch: 2026-01-01 (overridable via config).
        epoch = pd.Timestamp(c.epoch_date)
        start_day = epoch
        end_day = epoch + pd.Timedelta(days=c.n_days - 1)

        actual_start = max(pd.Timestamp(date_range.start).normalize(), start_day)
        actual_end = min(pd.Timestamp(date_range.end).normalize(), end_day)
        if actual_start > actual_end:
            return pd.DataFrame(columns=["timestamp", "stop_id", "route_id", "passenger_count"])

        # Build timestamps: every hour, every stop
        hours = pd.date_range(actual_start, actual_end + pd.Timedelta(hours=23), freq="h")
        # Cross join stops × hours
        stops_for_join = stops_df[["stop_id", "is_hub"]].copy()
        ridership_records = []
        for stop_id, is_hub in zip(stops_for_join["stop_id"], stops_for_join["is_hub"], strict=True):
            base = self._rng.uniform(c.ridership_min, c.ridership_max)
            if is_hub:
                base *= 2.0
            mults = self._hour_multipliers(hours)
            counts = np.maximum(0, self._rng.normal(base * mults, base * 0.1)).astype(int)

            # Find which routes serve this stop (without lambda in loop)
            stop_routes = routes_df[routes_df["stop_ids"].apply(lambda s, sid=stop_id: sid in s)]
            route_ids_for_stop = stop_routes["route_id"].tolist()
            if not route_ids_for_stop:
                continue
            route_id = int(route_ids_for_stop[0])

            for ts, cnt in zip(hours, counts, strict=True):
                if cnt > 0:
                    ridership_records.append(
                        {
                            "timestamp": ts,
                            "stop_id": int(stop_id),
                            "route_id": route_id,
                            "passenger_count": int(cnt),
                        }
                    )

        return pd.DataFrame(ridership_records)

    # ---- Helpers ----

    def _hour_multipliers(self, hours: pd.DatetimeIndex) -> np.ndarray:
        """Multipliers per hour, encoding daily + weekly patterns."""
        c = self.config
        mults = np.ones(len(hours))
        for i, ts in enumerate(hours):
            h = ts.hour
            wd = ts.weekday()  # 0 = Monday
            is_weekend = wd >= 5

            if h in c.peak_morning or h in c.peak_evening:
                mults[i] = c.peak_mult
            elif h < 6:
                mults[i] = c.night_mult
            else:
                mults[i] = 1.0

            if is_weekend:
                mults[i] *= c.weekend_mult

        return mults


__all__ = ["SyntheticConfig", "SyntheticSource"]
