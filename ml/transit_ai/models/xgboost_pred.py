"""XGBoost predictor for hourly ridership.

Tabular model on engineered features:
  - hour (0-23), weekday (0-6), is_weekend, hour_sin, hour_cos
  - month, day_of_year
  - stop_id (categorical), route_id (categorical)

Target: log1p(passenger_count) — RMSLE-friendly.
CI: 3 quantile models (q=0.1, 0.5, 0.9) → lower/upper.

GPU: используем device="cuda" если torch видит GPU; иначе cpu.

Контракт: см. .clinerules/08-contracts-and-artifacts.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from transit_ai.models.base import PredictionPoint, Predictor

# Квантили для CI (10%, 50%, 90%)
_QUANTILES: tuple[float, ...] = (0.1, 0.5, 0.9)

# Фиксированный список фичей — порядок важен (для inference и save/load)
FEATURE_NAMES: tuple[str, ...] = (
    "hour",
    "weekday",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "month",
    "day_of_year",
    "stop_id",
    "route_id",
)


def _make_features(ts: pd.Timestamp, stop_id: int, route_id: int) -> np.ndarray:
    """Vectorized feature extraction for one timestamp + (stop, route)."""
    hour = int(ts.hour)
    weekday = int(ts.weekday())
    is_weekend = int(weekday >= 5)
    hour_sin = float(np.sin(2 * np.pi * hour / 24))
    hour_cos = float(np.cos(2 * np.pi * hour / 24))
    month = int(ts.month)
    day_of_year = int(ts.dayofyear)
    return np.array(
        [
            hour,
            weekday,
            is_weekend,
            hour_sin,
            hour_cos,
            month,
            day_of_year,
            int(stop_id),
            int(route_id),
        ],
        dtype=np.float32,
    )


def _hourly_range(start: datetime, end: datetime) -> list[datetime]:
    """Hourly points [start, end)."""
    out: list[datetime] = []
    cur = start
    while cur < end:
        out.append(cur)
        cur += timedelta(hours=1)
    return out


def _resolve_device() -> str:
    """Return 'cuda' if available, else 'cpu'."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


@dataclass
class XGBoostPredictor(Predictor):
    """XGBoost quantile-regression predictor.

    Fits 3 boosters per quantile (0.1, 0.5, 0.9) for CI.
    """

    model_id: str = "xgboost_v1"
    kind: str = "xgboost"

    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    seed: int = 42

    # Fitted state
    boosters_: dict[float, xgb.Booster] = field(default_factory=dict)
    feature_names_: list[str] = field(default_factory=list)
    stop_route_default_: tuple[int, int] = (1, 1)  # fallback для unknown stops
    device_: str = "cpu"
    fitted_: bool = False

    def fit(self, ridership: pd.DataFrame) -> None:
        """Train 3 quantile boosters on ridership DataFrame.

        Expected columns: [timestamp, stop_id, route_id, passenger_count].
        """
        if ridership.empty:
            raise ValueError("Cannot fit XGBoostPredictor on empty ridership DataFrame")

        df = ridership.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        rows = []
        for r in df.itertuples(index=False):
            feat = _make_features(r.timestamp, int(r.stop_id), int(r.route_id))
            rows.append(feat)
        x_arr = np.vstack(rows).astype(np.float32)
        y = np.log1p(df["passenger_count"].to_numpy(dtype=np.float32))

        self.stop_route_default_ = (
            int(df["stop_id"].iloc[0]),
            int(df["route_id"].iloc[0]),
        )
        self.feature_names_ = list(FEATURE_NAMES)
        self.device_ = _resolve_device()

        dtrain = xgb.DMatrix(x_arr, label=y, feature_names=self.feature_names_)
        params_base: dict[str, object] = {
            "tree_method": "hist",
            "device": self.device_,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "seed": self.seed,
            "objective": "reg:quantileerror",
            "eval_metric": "quantile",
        }
        for q in _QUANTILES:
            params = dict(params_base)
            params["quantile_alpha"] = q
            booster = xgb.train(
                params=params,
                dtrain=dtrain,
                num_boost_round=self.n_estimators,
                verbose_eval=False,
            )
            self.boosters_[q] = booster

        self.fitted_ = True

    def _predict_single(
        self, stop_id: int, ts: datetime, route_id: int
    ) -> PredictionPoint:
        # Use default fallback for unknown (не критично для синтетики)
        x = _make_features(pd.Timestamp(ts), stop_id, route_id).reshape(1, -1)
        dmat = xgb.DMatrix(x, feature_names=self.feature_names_)
        q10_log = float(self.boosters_[0.1].predict(dmat)[0])
        q50_log = float(self.boosters_[0.5].predict(dmat)[0])
        q90_log = float(self.boosters_[0.9].predict(dmat)[0])
        value = float(np.expm1(q50_log))
        lower = float(np.expm1(q10_log))
        upper = float(np.expm1(q90_log))
        value = max(value, 0.0)
        lower = max(lower, 0.0)
        upper = max(upper, value)
        next_h = ts + timedelta(hours=1)
        return PredictionPoint(
            period_start=ts,
            period_end=next_h,
            value=value,
            lower=lower,
            upper=upper,
            stop_id=stop_id,
            route_id=route_id,
            model_id=self.model_id,
        )

    def predict(
        self,
        stop_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> list[PredictionPoint]:
        if not self.fitted_:
            raise RuntimeError("XGBoostPredictor not fitted; call fit() first")
        rt = self.stop_route_default_[1]
        return [
            self._predict_single(stop_id, ts, route_id=rt)
            for ts in _hourly_range(period_start, period_end)
        ]

    def save(self, path: str) -> None:
        """Save model + metadata via joblib + native XGBoost JSON."""
        import joblib

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        booster_dir = p.parent / (p.stem + "_boosters")
        booster_dir.mkdir(exist_ok=True)
        for q, booster in self.boosters_.items():
            booster.save_model(str(booster_dir / f"q{int(q * 100):02d}.json"))

        meta = {
            "model_id": self.model_id,
            "kind": self.kind,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "seed": self.seed,
            "feature_names": self.feature_names_,
            "stop_route_default": list(self.stop_route_default_),
            "device": self.device_,
        }
        joblib.dump({"meta": meta, "booster_dir": str(booster_dir)}, p)

    @classmethod
    def load(cls, path: str) -> XGBoostPredictor:
        import joblib

        p = Path(path)
        bundle = joblib.load(p)
        meta = bundle["meta"]
        booster_dir = Path(bundle["booster_dir"])

        predictor = cls(
            model_id=meta["model_id"],
            n_estimators=meta["n_estimators"],
            max_depth=meta["max_depth"],
            learning_rate=meta["learning_rate"],
            seed=meta["seed"],
        )
        predictor.feature_names_ = list(meta["feature_names"])
        predictor.stop_route_default_ = tuple(meta["stop_route_default"])
        predictor.device_ = meta["device"]

        for q in _QUANTILES:
            bpath = booster_dir / f"q{int(q * 100):02d}.json"
            if not bpath.exists():
                raise FileNotFoundError(f"Booster file missing: {bpath}")
            booster = xgb.Booster()
            booster.load_model(str(bpath))
            predictor.boosters_[q] = booster

        predictor.fitted_ = True
        return predictor


__all__ = ["XGBoostPredictor"]
