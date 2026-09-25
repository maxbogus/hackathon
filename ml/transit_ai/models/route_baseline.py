"""RouteBaselineMean — route-level baseline predictor (T-145, T-148, hackathon).

В отличие от stop-level BaselineMean, работает на уровне
(route_id, weekday, hour, day_type). Granularity = (route, date, hour) — то, что
требует WAPE-score платформы.

T-148: добавлена 4-я координата day_type ∈ {"workday","holiday","weekend"}.
Позволяет различать паттерны будни / выходные / праздники РФ. Из F-020: Сб/Вс
падают на 10pp относительно будних, праздники похожий эффект.

Fitted:
- table_: dict[(route_id, weekday, hour, day_type)] -> mean  (T-148)
- global_table_: dict[(weekday, hour, day_type)] -> mean
- legacy_table_: dict[(route_id, weekday, hour)] -> mean      (backward compat)
- legacy_global_table_: dict[(weekday, hour)] -> mean
- mean_: float (глобальный fallback)

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

from transit_ai.data.calendar_rf import get_day_type


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

    # Fitted state — T-148 (с day_type) + legacy (без day_type) для backward compat
    table_: dict[tuple[int, int, int, str], float] = field(default_factory=dict)
    global_table_: dict[tuple[int, int, str], float] = field(default_factory=dict)
    legacy_table_: dict[tuple[int, int, int], float] = field(default_factory=dict)
    legacy_global_table_: dict[tuple[int, int], float] = field(default_factory=dict)
    mean_: float = 0.0
    fitted_: bool = False

    # ---- Fit ----

    def fit(self, ridership: pd.DataFrame) -> None:
        """Build the lookup tables from ridership.

        Expected columns: [timestamp, route_id, date, hour, boardings]
        (or [timestamp, route_id, weekday, hour, boardings] if pre-computed)

        T-148: добавлена колонка day_type ∈ {"workday","holiday","weekend"}.
        Используется как 4-я координата в lookup-таблице для разделения
        паттернов будни/выходные/праздники (F-020).
        """
        if ridership.empty:
            raise ValueError(
                "Cannot fit RouteBaselineMean on empty ridership DataFrame"
            )

        df = ridership.copy()
        if "weekday" not in df.columns:
            df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
        # T-148: добавляем day_type если его нет
        if "day_type" not in df.columns:
            df["day_type"] = df["date"].apply(get_day_type)

        # T-148: per (route, weekday, hour, day_type) — основная таблица
        grouped = df.groupby(["route_id", "weekday", "hour", "day_type"])["boardings"]
        self.table_ = {key: float(val) for key, val in grouped.mean().items()}

        # T-148: global fallback per (weekday, hour, day_type)
        global_grouped = df.groupby(["weekday", "hour", "day_type"])["boardings"]
        self.global_table_ = {
            key: float(val) for key, val in global_grouped.mean().items()
        }

        # Legacy (backward compat — для pickle-файлов со старой схемой)
        legacy_grouped = df.groupby(["route_id", "weekday", "hour"])["boardings"]
        self.legacy_table_ = {
            key: float(val) for key, val in legacy_grouped.mean().items()
        }
        legacy_global = df.groupby(["weekday", "hour"])["boardings"]
        self.legacy_global_table_ = {
            key: float(val) for key, val in legacy_global.mean().items()
        }

        # Last resort
        self.mean_ = float(df["boardings"].mean())
        self.fitted_ = True

    # ---- Predict ----

    def _lookup(
        self, route_id: int, weekday: int, hour: int, day_type: str = "workday"
    ) -> float:
        """Lookup с fallback цепочкой (T-148):
        1) (route, weekday, hour, day_type)         — основная
        2) (route, weekday, hour)                   — legacy (без day_type)
        3) (weekday, hour, day_type)                 — global per day_type
        4) (weekday, hour)                           — global legacy
        5) global mean_
        """
        key4 = (route_id, weekday, hour, day_type)
        if key4 in self.table_:
            return self.table_[key4]
        key3 = (route_id, weekday, hour)
        if key3 in self.legacy_table_:
            return self.legacy_table_[key3]
        key_g4 = (weekday, hour, day_type)
        if key_g4 in self.global_table_:
            return self.global_table_[key_g4]
        key_g3 = (weekday, hour)
        if key_g3 in self.legacy_global_table_:
            return self.legacy_global_table_[key_g3]
        return self.mean_

    def predict_route(self, *, route: int, date: datetime, hour: int) -> float:
        """Предсказать boardings для одного (route, date, hour)."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        weekday = date.weekday()
        day_type = get_day_type(date.date() if isinstance(date, datetime) else date)
        return self._lookup(route, weekday, hour, day_type)

    def predict_batch(self, df: pd.DataFrame) -> np.ndarray:
        """Vectorized predict: ожидает колонки [route_id, date, hour]."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        if df.empty:
            return np.array([], dtype=np.float64)

        dates = pd.to_datetime(df["date"])
        weekdays = dates.dt.weekday.values
        # T-148: вычисляем day_type для каждого date
        day_types = dates.dt.date.map(get_day_type).values
        routes = df["route_id"].astype(int).values
        hours = df["hour"].astype(int).values

        n = len(df)
        out = np.empty(n, dtype=np.float64)
        for i in range(n):
            out[i] = self._lookup(
                int(routes[i]), int(weekdays[i]), int(hours[i]), str(day_types[i])
            )
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
                    "legacy_table_": self.legacy_table_,
                    "legacy_global_table_": self.legacy_global_table_,
                    "mean_": self.mean_,
                    "model_id": self.model_id,
                    "kind": self.kind,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> RouteBaselineMean:
        """Restore from disk. Backward-compat: если legacy поля нет — мигрируем."""
        with Path(path).open("rb") as f:
            data = pickle.load(f)
        m = cls(model_id=data.get("model_id", "route_baseline_v1"))
        m.table_ = data.get("table_", {})
        m.global_table_ = data.get("global_table_", {})
        # Backward-compat: старые pickle без legacy_*
        m.legacy_table_ = data.get("legacy_table_", data.get("table_", {}))
        m.legacy_global_table_ = data.get(
            "legacy_global_table_", data.get("global_table_", {})
        )
        m.mean_ = data["mean_"]
        m.fitted_ = True
        return m


__all__ = ["RouteBaselineMean"]
