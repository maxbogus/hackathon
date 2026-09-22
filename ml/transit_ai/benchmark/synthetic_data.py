"""Synthetic ridership aggregation for benchmark.

Заменяет прежний hardcoded `_synthetic_data()` в cli.py.
Использует `transit_ai.data.synthetic.SyntheticSource` — общий генератор
синтетики для всех pipeline (training, predict, calibrate, benchmark).

Контракт: возвращает DataFrame с колонками `[date, value, n_stops]` —
по одной строке на день, `value` = суммарный пассажиропоток за день.

Используется в:
- `transit_ai.benchmark.cli.run_benchmark_sweep` (T-039)
- `transit_ai.benchmark.runner.run_single_benchmark` (через переданный df)

Почему отдельный модуль, а не SyntheticSource напрямую:
- Benchmark ожидает daily aggregate (не hourly × all stops)
- Cross-package consistency: один источник синтетики — один формат
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from transit_ai.data.base import DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource


def load_synthetic_benchmark_data(
    n_days: int = 35,
    seed: int = 42,
    n_stops: int = 10,
    n_routes: int = 5,
) -> pd.DataFrame:
    """Сгенерить synthetic ridership через SyntheticSource и агрегировать по дням.

    Args:
        n_days: количество дней синтетики (28 train + 7 holdout по умолчанию).
        seed: random seed (R6 reproducibility).
        n_stops: количество остановок (default 10 для быстрого smoke).
        n_routes: количество маршрутов.

    Returns:
        DataFrame с колонками:
        - `date` (Timestamp): начало дня
        - `value` (float64): суммарный пассажиропоток за день
        - `n_stops` (int64): сколько остановок активно в этот день

    Raises:
        ValueError: если n_days < 2 (нельзя сделать walk-forward split).
    """
    if n_days < 2:
        raise ValueError(f"n_days must be >= 2 (got {n_days})")

    src = SyntheticSource(
        SyntheticConfig(n_days=n_days, seed=seed, n_stops=n_stops, n_routes=n_routes)
    )
    epoch = datetime(2026, 1, 1)  # noqa: DTZ001 — SyntheticSource сравнивает tz-naive внутри
    df_hourly = src.load_ridership(DateRange(epoch, epoch + timedelta(days=n_days - 1)))

    if df_hourly.empty:
        # SyntheticSource может вернуть пустой df при каких-то границах; возвращаем нули.
        dates = pd.date_range(epoch, periods=n_days, freq="D")
        return pd.DataFrame({"date": dates, "value": 0.0, "n_stops": 0})

    df_hourly = df_hourly.copy()
    df_hourly["date"] = pd.to_datetime(df_hourly["timestamp"]).dt.normalize()

    grouped = df_hourly.groupby("date")
    out = grouped.agg(
        value=("passenger_count", "sum"),
        n_stops=("stop_id", "nunique"),
    ).reset_index()

    # Гарантируем, что все дни присутствуют (включая те, где пассажиров = 0)
    full_dates = pd.date_range(
        df_hourly["date"].min(), df_hourly["date"].max(), freq="D"
    )
    out = out.set_index("date").reindex(full_dates, fill_value=0.0).reset_index()
    out = out.rename(columns={"index": "date"})
    return out


__all__ = ["load_synthetic_benchmark_data"]
