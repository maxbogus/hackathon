"""XGBoost predictor для route-level данных хакатона (T-152, F-020, F-023).

Адаптация существующего XGBoostPredictor под:
- route-only данные (нет stop_id) → избегаем overfitting на stop-категории
- target = boardings (не passenger_count)
- дополнительные фичи: is_holiday (T-148), lag_24h/168h/730h, rolling_mean

ВАЖНО: лаг-фичи вычисляются на полном DataFrame train+holdout (sorted by date),
поэтому fit() принимает ВСЕ данные, не только train period.

INFERENCE FIX (T-152-fallback): на submission period у нас нет boardings,
поэтому lag/rolling = 0 приводит к OOD prediction (sum_preds << реальность).
Решение: передавать `lag_lookup` (mean по (route, weekday, hour) из train)
в predict_batch / predict_with_ci. Если не передать — fallback на 0 (legacy).

Артефакт в ml/artifacts/<model_id>/:
    model.pkl        — XGBoostPredictor через joblib
    meta.json        — model_id, git_commit, train_data_hash, seed, metrics
    feature_names.json — список фичей (для inference)
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from transit_ai.data.calendar_rf import get_day_type

# Фичи в порядке (порядок важен для DMatrix)
FEATURE_NAMES: tuple[str, ...] = (
    "hour",
    "weekday",
    "month",
    "hour_sin",
    "hour_cos",
    "is_weekend",
    "is_holiday",
    "day_type_workday",
    "day_type_weekend",
    "day_type_holiday",
    "route_id",
    "lag_24h",
    "lag_168h",
    "lag_730h",
    "rolling_mean_24h",
    "rolling_mean_168h",
    "rolling_mean_30d",
)


def build_lag_lookup(train_df: pd.DataFrame) -> dict[tuple[int, int, int], float]:
    """Построить lookup {route, weekday, hour} -> mean(boardings) из train данных.

    Используется на inference для fallback значений lag/rolling фичей когда
    у нас нет boardings (submission period, T-152-fallback).

    Returns:
        dict: ключ = (route_id, weekday, hour), значение = mean boardings.
        Маршруты без данных в train получат route-mean как fallback.
    """
    df = train_df.copy()
    if "weekday" not in df.columns:
        df["weekday"] = pd.to_datetime(df["timestamp"]).dt.weekday
    grouped = df.groupby(["route_id", "weekday", "hour"])["boardings"]
    lookup: dict[tuple[int, int, int], float] = {
        key: float(val) for key, val in grouped.mean().items()
    }
    # Fallback для route без полного покрытия: route-mean
    route_means = df.groupby("route_id")["boardings"].mean()
    for route, mean_val in route_means.items():
        for wd in range(7):
            for h in range(24):
                key = (int(route), wd, h)
                if key not in lookup:
                    lookup[key] = float(mean_val)
    return lookup


def _make_features(
    df: pd.DataFrame,
    target: pd.Series | None = None,
    lag_lookup: dict[tuple[int, int, int], float] | None = None,
) -> tuple[pd.DataFrame, pd.Series | None]:
    """Создать матрицу фичей + target.

    df должен содержать: [timestamp, route_id, date, hour, boardings (если есть)]
    Вычисляет: weekday, month, hour_sin/cos, is_weekend, is_holiday, day_type_*

    Lag/rolling features:
    - если df содержит boardings (training mode): вычисляются как shift() в группе
    - если НЕТ boardings (inference mode) И lag_lookup передан: используем lookup[(route, weekday, hour)]
    - если НЕТ boardings И lookup=None: 0 (legacy OOD, не рекомендуется)
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["weekday"] = df["timestamp"].dt.weekday
    df["month"] = df["timestamp"].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # is_holiday из T-148 calendar
    df["is_holiday"] = (
        df["timestamp"].dt.date.map(get_day_type).eq("holiday").astype(int)
    )

    # day_type one-hot (3 колонки, drop reference = workday)
    df["day_type"] = df["timestamp"].dt.date.map(get_day_type)
    df["day_type_workday"] = (df["day_type"] == "workday").astype(int)
    df["day_type_weekend"] = (df["day_type"] == "weekend").astype(int)
    df["day_type_holiday"] = (df["day_type"] == "holiday").astype(int)

    # lag features: сортируем по (route, date, hour) и groupby route
    df = df.sort_values(["route_id", "timestamp"]).reset_index(drop=True)

    if "boardings" in df.columns and target is None:
        df["boardings"] = df["boardings"].astype(float)
        # lag фичи — shift внутри группы route_id
        # 24h назад = тот же route, тот же час, вчера
        df["lag_24h"] = df.groupby("route_id")["boardings"].shift(24)
        df["lag_168h"] = df.groupby("route_id")["boardings"].shift(168)
        df["lag_730h"] = df.groupby("route_id")["boardings"].shift(730)
        # rolling means по тому же route (shift(1) чтобы не использовать текущее значение)
        df["rolling_mean_24h"] = (
            df.groupby("route_id")["boardings"]
            .shift(1)
            .rolling(24, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        df["rolling_mean_168h"] = (
            df.groupby("route_id")["boardings"]
            .shift(1)
            .rolling(168, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        df["rolling_mean_30d"] = (
            df.groupby("route_id")["boardings"]
            .shift(1)
            .rolling(24 * 30, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        # NaN в начале ряда — заполняем глобальным mean по route
        for col in (
            "lag_24h",
            "lag_168h",
            "lag_730h",
            "rolling_mean_24h",
            "rolling_mean_168h",
            "rolling_mean_30d",
        ):
            df[col] = df[col].fillna(
                df.groupby("route_id")["boardings"].transform("mean")
            )
        # если всё ещё NaN (route без данных) — fallback на 0
        df[col] = df[col].fillna(0)
    elif lag_lookup is not None:
        # T-152-fallback: inference mode + lag_lookup передан
        # Используем mean из train по (route, weekday, hour) для всех 6 фичей
        lookup_vals: list[float] = []
        for _, r in df.iterrows():
            key = (int(r["route_id"]), int(r["weekday"]), int(r["hour"]))
            lookup_vals.append(float(lag_lookup.get(key, 0.0)))
        lookup_series = pd.Series(lookup_vals, index=df.index)
        for col in (
            "lag_24h",
            "lag_168h",
            "lag_730h",
            "rolling_mean_24h",
            "rolling_mean_168h",
            "rolling_mean_30d",
        ):
            df[col] = lookup_series
    else:
        # Legacy inference mode (OOD, не рекомендуется): lag = 0
        for col in (
            "lag_24h",
            "lag_168h",
            "lag_730h",
            "rolling_mean_24h",
            "rolling_mean_168h",
            "rolling_mean_30d",
        ):
            df[col] = 0.0

    X = df[list(FEATURE_NAMES)].copy()
    y = (
        target
        if target is not None
        else (df["boardings"] if "boardings" in df.columns else None)
    )
    return X, y


@dataclass
class XGBoostRoutePredictor:
    """XGBoost predictor для route-level данных (T-152).

    Обучает 3 quantile boosters (q=0.1, 0.5, 0.9) для confidence intervals.
    """

    model_id: str = "xgboost_v2"
    kind: str = "xgboost_route"

    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    seed: int = 42

    # Fitted state
    booster_: Any = None  # xgb.Booster (median)
    boosters_: dict[float, xgb.Booster] = field(default_factory=dict)
    feature_names_: list[str] = field(default_factory=list)
    fitted_: bool = False

    def fit(self, ridership: pd.DataFrame) -> None:
        """Train XGBoost на route-level данных.

        ridership должен содержать: [timestamp, route_id, date, hour, boardings]
        Полный ряд (train + holdout) для корректных lag features.
        """
        if ridership.empty:
            raise ValueError("Cannot fit XGBoostRoutePredictor on empty data")
        required = {"timestamp", "route_id", "boardings"}
        missing = required - set(ridership.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        df = ridership.copy()
        if "date" not in df.columns:
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        if "hour" not in df.columns:
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        X, y = _make_features(df)
        if y is None:
            raise ValueError("No target column found")

        self.feature_names_ = list(FEATURE_NAMES)

        # XGBoost: 3 quantile boosters для CI
        dtrain = xgb.DMatrix(
            X.values.astype(np.float32),
            label=np.log1p(y.values.astype(np.float32)),
            feature_names=self.feature_names_,
        )
        params_base = {
            "tree_method": "hist",
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "seed": self.seed,
            "verbosity": 0,
        }
        for q in (0.1, 0.5, 0.9):
            params = dict(params_base)
            params["objective"] = "reg:quantileerror"
            params["quantile_alpha"] = q
            booster = xgb.train(
                params=params,
                dtrain=dtrain,
                num_boost_round=self.n_estimators,
            )
            self.boosters_[q] = booster
        self.booster_ = self.boosters_[0.5]  # median для быстрого predict
        self.fitted_ = True

    def predict_batch(
        self,
        df: pd.DataFrame,
        lag_lookup: dict[tuple[int, int, int], float] | None = None,
    ) -> np.ndarray:
        """Predict median (q=0.5) для batch of (route, date, hour).

        df: должен содержать [route_id, date, hour] (timestamp вычислим).
        lag_lookup (T-152-fallback): dict[(route, weekday, hour)] -> mean boardings
        из train данных. Используется если df не содержит boardings (submission period).
        """
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        if df.empty:
            return np.array([], dtype=np.float64)
        df = df.copy()
        if "timestamp" not in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"]) + pd.to_timedelta(
                df["hour"], unit="h"
            )
        X, _ = _make_features(df, lag_lookup=lag_lookup)
        dmat = xgb.DMatrix(
            X.values.astype(np.float32), feature_names=self.feature_names_
        )
        preds_log = self.booster_.predict(dmat)
        preds = np.expm1(preds_log)
        return np.maximum(preds, 0.0)

    def predict_with_ci(
        self,
        df: pd.DataFrame,
        lag_lookup: dict[tuple[int, int, int], float] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict с CI: (median, lower=q0.1, upper=q0.9). lag_lookup — see predict_batch."""
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        if df.empty:
            return np.array([]), np.array([]), np.array([])
        df = df.copy()
        if "timestamp" not in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"]) + pd.to_timedelta(
                df["hour"], unit="h"
            )
        X, _ = _make_features(df)
        dmat = xgb.DMatrix(
            X.values.astype(np.float32), feature_names=self.feature_names_
        )
        lower = np.maximum(np.expm1(self.boosters_[0.1].predict(dmat)), 0.0)
        median = np.maximum(np.expm1(self.boosters_[0.5].predict(dmat)), 0.0)
        upper = np.maximum(np.expm1(self.boosters_[0.9].predict(dmat)), 0.0)
        return median, lower, upper

    def save(self, path: str) -> None:
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Save boosters separately (XGBoost native)
        booster_dir = p.parent / (p.stem + "_boosters")
        booster_dir.mkdir(exist_ok=True)
        for q, booster in self.boosters_.items():
            booster.save_model(str(booster_dir / f"q{int(q * 100):02d}.json"))
        # Save meta + boosters_dir via pickle
        meta = {
            "model_id": self.model_id,
            "kind": self.kind,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "seed": self.seed,
            "feature_names": self.feature_names_,
        }
        with p.open("wb") as f:
            pickle.dump({"meta": meta, "booster_dir": str(booster_dir)}, f)

    @classmethod
    def load(cls, path: str) -> XGBoostRoutePredictor:
        p = Path(path)
        with p.open("rb") as f:
            bundle = pickle.load(f)
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
        for q in (0.1, 0.5, 0.9):
            bpath = booster_dir / f"q{int(q * 100):02d}.json"
            booster = xgb.Booster()
            booster.load_model(str(bpath))
            predictor.boosters_[q] = booster
        predictor.booster_ = predictor.boosters_[0.5]
        predictor.fitted_ = True
        return predictor


__all__ = ["FEATURE_NAMES", "XGBoostRoutePredictor", "build_lag_lookup"]
