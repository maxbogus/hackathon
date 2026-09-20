"""BaselineMean predictor: mean passenger count per (stop_id, weekday, hour).

Самый тупой baseline: для каждой остановки храним среднее за (weekday, hour).
Prediction = sum of hour means внутри [period_start, period_end].
Confidence interval: lower/upper = sum of (mean ± 1 std).

RMSLE на синтетике (test split, 7 дней): ~0.28 (см. benchmark).
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from transit_ai.models.base import PredictionPoint, Predictor


@dataclass
class BaselineMean(Predictor):
    """Mean-by-time-bucket predictor.

    Fits a dict mapping (stop_id, weekday, hour) -> (mean, std).
    Cold-start fallback: global mean over (weekday, hour).
    """

    model_id: str = "baseline_v1"
    kind: str = "baseline"

    # Fitted state
    table_: dict[tuple[int, int, int], tuple[float, float]] = field(default_factory=dict)
    global_table_: dict[tuple[int, int], tuple[float, float]] = field(default_factory=dict)
    fitted_: bool = False

    # ---- Fit ----

    def fit(self, ridership: pd.DataFrame) -> None:
        """Build the lookup tables from a ridership DataFrame.

        Expected columns: [timestamp, stop_id, route_id, passenger_count]
        """
        if ridership.empty:
            raise ValueError("Cannot fit BaselineMean on empty ridership DataFrame")

        df = ridership.copy()
        df["weekday"] = pd.to_datetime(df["timestamp"]).dt.weekday
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        grouped = df.groupby(["stop_id", "weekday", "hour"])["passenger_count"]
        stats = grouped.agg(["mean", "std"]).reset_index()
        for row in stats.itertuples(index=False):
            row_dict = row._asdict()
            key = (int(row_dict["stop_id"]), int(row_dict["weekday"]), int(row_dict["hour"]))
            mean = float(row_dict["mean"])
            std = float(row_dict["std"]) if not pd.isna(row_dict["std"]) else 0.0
            self.table_[key] = (mean, std)

        # Global fallback (по (weekday, hour)) для новых остановок
        global_grouped = df.groupby(["weekday", "hour"])["passenger_count"]
        global_stats = global_grouped.agg(["mean", "std"]).reset_index()
        for row in global_stats.itertuples(index=False):
            row_dict = row._asdict()
            key = (int(row_dict["weekday"]), int(row_dict["hour"]))
            mean = float(row_dict["mean"])
            std = float(row_dict["std"]) if not pd.isna(row_dict["std"]) else 0.0
            self.global_table_[key] = (mean, std)

        self.fitted_ = True

    # ---- Predict ----

    def _bucket_value(self, stop_id: int, weekday: int, hour: int) -> tuple[float, float]:
        """Mean and std for one (stop, weekday, hour) bucket."""
        if (stop_id, weekday, hour) in self.table_:
            return self.table_[(stop_id, weekday, hour)]
        if (weekday, hour) in self.global_table_:
            return self.global_table_[(weekday, hour)]
        return (0.0, 0.0)

    def predict(
        self,
        stop_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> list[PredictionPoint]:
        if not self.fitted_:
            raise RuntimeError("BaselineMean must be fitted before predict()")

        points: list[PredictionPoint] = []
        cur = period_start
        while cur < period_end:
            next_hour = cur + timedelta(hours=1)
            mean, std = self._bucket_value(stop_id, cur.weekday(), cur.hour)
            points.append(
                PredictionPoint(
                    period_start=cur,
                    period_end=next_hour,
                    value=max(0.0, mean),
                    lower=max(0.0, mean - std),
                    upper=mean + std,
                    stop_id=stop_id,
                    model_id=self.model_id,
                )
            )
            cur = next_hour
        return points

    # ---- Persistence ----

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as f:
            pickle.dump(
                {
                    "model_id": self.model_id,
                    "kind": self.kind,
                    "table": self.table_,
                    "global_table": self.global_table_,
                    "fitted": self.fitted_,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> BaselineMean:
        with Path(path).open("rb") as f:
            data: dict[str, Any] = pickle.load(f)
        inst = cls(model_id=data["model_id"])
        inst.table_ = data["table"]
        inst.global_table_ = data["global_table"]
        inst.fitted_ = data["fitted"]
        return inst


__all__ = ["BaselineMean"]
