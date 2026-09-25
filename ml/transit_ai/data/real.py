"""Real data source для датасета хакатона (T-143).

Читает `data/real/labels/labels_day_{train,test}.csv` (агрегаты по
`route;date;hour;boardings`). Не зависит от stop-level детализации (F-015):
геопривязка остановок покрывает лишь {1,5,7,11,12} из 10 маршрутов, а метрика
WAPE-score считается на уровне (route, date, hour) — основной unit прогноза.

Контракт (см. `.clinerules/02-architecture.md` → DataSource ABC):
- load_stops() — пустой DataFrame (stop-level опционален)
- load_routes() — 10 трамвайных маршрутов {1,5,7,11,12,17,25,26,28,50}
- load_ridership(date_range) — DataFrame[timestamp, route_id, date, hour, boardings]

Конкурентное преимущество:
- Прямой read labels → быстро (нет groupby по 49M строкам)
- Контракт совпадает с submission.csv форматом
- validate() ловит ошибки данных на старте
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from transit_ai.data.base import DataSource, DateRange


class RealSource(DataSource):
    """Read hackathon route-level ridership data from labels_day_*.csv.

    Returns DataFrame in unified contract:
        [timestamp, route_id, date, hour, boardings]
    where timestamp = pd.Timestamp(date) + pd.Timedelta(hours=hour).
    """

    ROUTES: tuple[int, ...] = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)
    _REPO_ROOT: Path = Path(__file__).resolve().parents[3]  # hackathon/
    DEFAULT_LABELS_DIR: Path = _REPO_ROOT / "data" / "real" / "labels"

    def __init__(self, labels_dir: Path | None = None) -> None:
        self.labels_dir: Path = labels_dir or self.DEFAULT_LABELS_DIR

    def load_stops(self) -> pd.DataFrame:
        """Stop-level не нужен для WAPE-метрики (F-015). Возвращаем пустой DF."""
        return pd.DataFrame(columns=["stop_id", "name", "lat", "lon", "route_ids"])

    def load_routes(self) -> pd.DataFrame:
        """Все 10 маршрутов хакатона с человекочитаемыми именами."""
        return pd.DataFrame(
            {
                "route_id": list(self.ROUTES),
                "name": [f"Трамвай {r}" for r in self.ROUTES],
            }
        )

    def load_ridership(self, date_range: DateRange) -> pd.DataFrame:
        """Загрузить boardings в [date_range.start, date_range.end]."""
        train = self._read_labels_file("labels_day_train.csv")
        test = self._read_labels_file("labels_day_test.csv")
        all_df = pd.concat([train, test], ignore_index=True)

        # Filter by date_range (inclusive)
        all_df["date"] = pd.to_datetime(all_df["date"])
        start = pd.Timestamp(date_range.start.date())
        end = pd.Timestamp(date_range.end.date())
        mask = (all_df["date"] >= start) & (all_df["date"] <= end)
        filtered = all_df[mask].copy()

        # Contract columns
        filtered["timestamp"] = filtered["date"] + pd.to_timedelta(
            filtered["hour"], unit="h"
        )
        filtered["route_id"] = filtered["route"].astype(int)
        return filtered[
            ["timestamp", "route_id", "date", "hour", "boardings"]
        ].reset_index(drop=True)

    def _read_labels_file(self, filename: str) -> pd.DataFrame:
        path = self.labels_dir / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Labels file not found: {path}. Place {filename} in {self.labels_dir}."
            )
        df = pd.read_csv(path, sep=";", encoding="utf-8")
        self.validate(df)
        return df

    @staticmethod
    def validate(df: pd.DataFrame) -> None:
        """Raise ValueError on schema violations (negative, NaN, bad hours, missing cols)."""
        required = {"route", "date", "hour", "boardings"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        if (df["boardings"] < 0).any():
            n = int((df["boardings"] < 0).sum())
            raise ValueError(f"Negative boardings: {n} rows")

        if not df["hour"].between(0, 23).all():
            bad = sorted(df[~df["hour"].between(0, 23)]["hour"].unique().tolist())
            raise ValueError(f"Invalid hour values (must be 0..23): {bad}")

        if df["boardings"].isna().any():
            n = int(df["boardings"].isna().sum())
            raise ValueError(f"NaN boardings: {n} rows")


__all__ = ["RealSource"]
