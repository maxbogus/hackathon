"""RouteBaselineMean — route-level baseline predictor (T-145, hackathon).

В отличие от stop-level BaselineMean, работает на уровне (route_id, weekday, hour).
Granularity = (route, date, hour) — то, что требует WAPE-score платформы.

Fitted:
- table_: dict[(route_id, weekday, hour)] -> mean
- global_table_: dict[(weekday, hour)] -> mean (fallback для новых маршрутов)
- mean_: float (глобальный fallback если (weekday, hour) нет)

Predictions:
- predict_route(route, date, hour) -> float (one value)
- predict_batch(df) -> np.ndarray (vectorized)
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class RouteBaselineMean:
    """Mean-by-route-weekday-hour predictor.

    Fits a dict mapping (route_id, weekday, hour) -> mean boardings.
    Cold-start fallback: global mean by (weekday, hour), then global mean.

    WAPE-score на hackathon holdout (сен–окт 2025): TBD (зависит от модели).
    Ожидание: 0.55–0.65 (baseline без exogenous фичей).
    """

    model_id: str = "route_baseline_v1"
    kind: str = "route_baseline"

    # Fitted state
    table_: dict[tuple[int, int, int], float] = field(default_factory=dict)
    global_table_: dict[tuple[int, int], float] = field(default_factory=dict)
    mean_: float = 0.0
    fitted_: bool = False

    # ---- Fit ----

    def fit(self, ridership: pd.DataFrame) -> None:
        """Build the lookup tables from ridership.

        Expected columns: [timestamp, route_id, date, hour, boardings]
        (or [timestamp, route_id, weekday, hour, boardings] if pre-computed)
        """
        if ridership.empty:
            raise ValueError(
                "Cannot fit RouteBaselineMean on empty ridership DataFrame"
            )

        df = ridership.copy()
        if "weekday" not in df.columns:
            df["weekday"] = pd.to_datetime(df["date"]).dt.weekday

        # Per (route, weekday, hour)
        grouped = df.groupby(["route_id", "weekday", "hour"])["boardings"]
        self.table_ = {key: float(val) for key, val in grouped.mean().items()}

        # Global fallback per (weekday, hour)
        global_grouped = df.groupby(["weekday", "hour"])["boardings"]
        self.global_table_ = {
            key: float(val) for key, val in global_grouped.mean().items()
        }

        # Last resort
        self.mean_ = float(df["boardings"].mean())
        self.fitted_ = True

    # ---- Predict ----

    def _lookup(self, route_id: int, weekday: int, hour: int) -> float:
        if (route_id, weekday, hour) in self.table_:
            return self.table_[(route_id, weekday, hour)]
        if (weekday, hour) in self.global_table_:
            return self.global_table_[(weekday, hour)]
        return self.mean_

    def predict_route(self, *, route: int, date: datetime, hour: int) -> float:
        """Предсказать boardings для одного (route, date, hour)."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        weekday = date.weekday()
        return self._lookup(route, weekday, hour)

    def predict_batch(self, df: pd.DataFrame) -> np.ndarray:
        """Vectorized predict: ожидает колонки [route_id, date, hour]."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        if df.empty:
            return np.array([], dtype=np.float64)

        dates = pd.to_datetime(df["date"])
        weekdays = dates.dt.weekday.values
        routes = df["route_id"].astype(int).values
        hours = df["hour"].astype(int).values

        n = len(df)
        out = np.empty(n, dtype=np.float64)
        for i in range(n):
            out[i] = self._lookup(int(routes[i]), int(weekdays[i]), int(hours[i]))
        return out

    # ---- Persistence ----

    def save(self, path: str) -> None:
        """Save model to disk (pickle)."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as f:
            pickle.dump(
                {
                    "table_": self.table_,
                    "global_table_": self.global_table_,
                    "mean_": self.mean_,
                    "model_id": self.model_id,
                    "kind": self.kind,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> RouteBaselineMean:
        """Restore from disk."""
        with Path(path).open("rb") as f:
            data = pickle.load(f)
        m = cls(model_id=data.get("model_id", "route_baseline_v1"))
        m.table_ = data["table_"]
        m.global_table_ = data["global_table_"]
        m.mean_ = data["mean_"]
        m.fitted_ = True
        return m


__all__ = ["RouteBaselineMean"]
