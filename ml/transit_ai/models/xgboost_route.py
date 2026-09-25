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
from transit_ai.data.seasonal_calendar import get_seasonal_features
from transit_ai.data.spravochnik_geo import build_route_geo_features
from transit_ai.data.validators_lookup import get_validators_features
from transit_ai.data.weather_openmeteo import get_weather_features

# Фичи в порядке (порядок важен для DMatrix)
# Geo-фичи из справочника (T-156)
_GEO_FEATURES: tuple[str, ...] = (
    "lat_mid", "lon_mid", "dist_center_km",
    "n_stops_log", "place_id_enc",
)

# Внешние сезонные фичи (T-160, T-161, T-162)
_EXTERNAL_FEATURES: tuple[str, ...] = (
    # T-160: school/uni/vacation
    "is_school_break", "is_school_start_day", "is_mass_vacation",
    "is_pre_holiday", "days_to_school_start", "days_to_new_year",
    "is_workday_calendar_rf", "uni_session_active",
    # T-161: weather
    "temp_max", "temp_min", "precipitation_sum", "snowfall_sum", "wind_speed_max",
    # T-162: validators
    "n_validators_mean", "n_trams_mean",
)

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
    *_GEO_FEATURES,  # T-156
    *_EXTERNAL_FEATURES,  # T-160, T-161, T-162
    "lag_24h",
    "lag_168h",
    "lag_730h",
    "rolling_mean_24h",
    "rolling_mean_168h",
    "rolling_mean_30d",
)


def _get_geo_lookup() -> dict[int, dict[str, float]]:
    """Ленивая загрузка geo-фичей из справочника + user-data.

    Returns:
        dict[int, dict]: ключ = route_id, значение = {lat_mid, lon_mid, ...}.
    """
    geo = build_route_geo_features()
    result: dict[int, dict[str, float]] = {}
    for _, row in geo.iterrows():
        result[int(row["route"])] = {
            "lat_mid": float(row["lat_mid"]),
            "lon_mid": float(row["lon_mid"]),
            "dist_center_km": float(row["dist_center_km"]),
            "n_stops_log": float(np.log1p(row["n_stops"])),
            "place_id_enc": float(row["primary_place_id"] - 39706),  # 39706 -> 0
        }
    return result


_GEO_CACHE: dict[int, dict[str, float]] | None = None


def _geo_for_route(route_id: int) -> dict[str, float]:
    """Получить geo-фичи для маршрута (с кэшем)."""
    global _GEO_CACHE
    if _GEO_CACHE is None:
        _GEO_CACHE = _get_geo_lookup()
    return _GEO_CACHE.get(int(route_id), {
        "lat_mid": 0.0, "lon_mid": 0.0, "dist_center_km": 0.0,
        "n_stops_log": 0.0, "place_id_enc": 0.0,
    })


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

    # T-156: geo-фичи из справочника
    geo_lookup = _get_geo_lookup()
    df["lat_mid"] = df["route_id"].map(
        lambda r: geo_lookup.get(int(r), {}).get("lat_mid", 0.0)
    )
    df["lon_mid"] = df["route_id"].map(
        lambda r: geo_lookup.get(int(r), {}).get("lon_mid", 0.0)
    )
    df["dist_center_km"] = df["route_id"].map(
        lambda r: geo_lookup.get(int(r), {}).get("dist_center_km", 0.0)
    )
    df["n_stops_log"] = df["route_id"].map(
        lambda r: geo_lookup.get(int(r), {}).get("n_stops_log", 0.0)
    )
    df["place_id_enc"] = df["route_id"].map(
        lambda r: geo_lookup.get(int(r), {}).get("place_id_enc", 0.0)
    )

    # T-160, T-161, T-162: внешние фичи по дате и (route, weekday, hour)
    # Сначала seasonal + weather по дате
    seasonal_cache = {}
    weather_cache = {}
    date_list = pd.to_datetime(df["timestamp"]).dt.date
    for d_val in set(date_list):
        seasonal_cache[d_val] = get_seasonal_features(d_val)
        weather_cache[d_val] = get_weather_features(d_val)

    seasonal_df = pd.DataFrame([seasonal_cache[d] for d in date_list], index=df.index)
    weather_df = pd.DataFrame([weather_cache[d] for d in date_list], index=df.index)
    df = pd.concat([df, seasonal_df, weather_df], axis=1)

    # Validators lookup: per (route, weekday, hour)
    val_cache = {}
    routes = df["route_id"].astype(int).values
    weekdays = df["weekday"].astype(int).values
    hours = df["hour"].astype(int).values
    n_validators = np.zeros(len(df), dtype=np.float32)
    n_trams = np.zeros(len(df), dtype=np.float32)
    for i in range(len(df)):
        key = (int(routes[i]), int(weekdays[i]), int(hours[i]))
        if key not in val_cache:
            val_cache[key] = get_validators_features(*key)
        n_validators[i] = val_cache[key]["n_validators_mean"]
        n_trams[i] = val_cache[key]["n_trams_mean"]
    df["n_validators_mean"] = n_validators
    df["n_trams_mean"] = n_trams

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

    def predict_recursive(
        self,
        history: pd.DataFrame,
        future_grid: pd.DataFrame,
        recompute_every_days: int = 7,
    ) -> np.ndarray:
        """T-153: Rolling-window forecast (direct, NOT pure recursive).

        F-025 показал: чистый recursive (использовать предсказания как lag для
        следующего дня) ДЕГРАДИРУЕТ с каждой итерацией. F-026 — нужно
        фундаментально решить lag=0 OOD.

        Правильная стратегия (direct multi-step, Hyndman):
        1. Для каждого дня в future_grid:
           - Присоединяем его к history (с реальными boardings до cutoff_date)
           - Внутри окна из `recompute_every_days` дней — НЕ обновляем history
             предсказаниями (избегаем drift)
           - Lag/rolling features берутся из extended_history (реальные данные
             для дней ≤ cutoff, NaN для будущего → fallback в _make_features на
             route mean).
        2. Predict все ячейки окна одним DMatrix.
        3. На СЛЕДУЮЩЕМ окне — добавляем предсказания в history (best-effort),
           но НЕ полагаемся на них — features всё равно используют реальные
           данные когда доступны.

        Args:
            history: [timestamp, route_id, date, hour, boardings]. Реальные данные.
            future_grid: [timestamp, route_id, date, hour]. Полная сетка.
            recompute_every_days: размер окна (default 7).

        Returns:
            np.ndarray длиной len(future_grid).
        """
        if not self.fitted_:
            raise RuntimeError("Model not fitted. Call fit() first.")
        if future_grid.empty:
            return np.array([], dtype=np.float64)

        history = history.copy()
        if "timestamp" not in history.columns:
            history["timestamp"] = pd.to_datetime(history["date"]) + pd.to_timedelta(
                history["hour"], unit="h"
            )
        future_grid = future_grid.copy()
        if "timestamp" not in future_grid.columns:
            future_grid["timestamp"] = pd.to_datetime(
                future_grid["date"]
            ) + pd.to_timedelta(future_grid["hour"], unit="h")

        # Сохраняем оригинальный порядок
        future_grid = future_grid.reset_index(drop=True)
        future_grid["_orig_idx"] = np.arange(len(future_grid))

        history = history.sort_values(["timestamp", "route_id"]).reset_index(drop=True)
        future_grid_sorted = future_grid.sort_values(
            ["timestamp", "route_id"]
        ).reset_index(drop=True)

        result = np.zeros(len(future_grid), dtype=np.float64)
        extended_history = history.copy()

        unique_days = sorted(future_grid_sorted["timestamp"].dt.normalize().unique())
        n_windows = (
            len(unique_days) + recompute_every_days - 1
        ) // recompute_every_days

        for w_idx in range(n_windows):
            win_start = w_idx * recompute_every_days
            win_end = min(win_start + recompute_every_days, len(unique_days))
            window_days = unique_days[win_start:win_end]

            win_mask = future_grid_sorted["timestamp"].dt.normalize().isin(window_days)
            win_rows = future_grid_sorted[win_mask].copy()
            win_rows["boardings"] = np.nan

            combined = pd.concat([extended_history, win_rows], ignore_index=True)
            combined = combined.sort_values(["timestamp", "route_id"]).reset_index(
                drop=True
            )

            X, _ = _make_features(combined, target=None)
            win_X = X.tail(len(win_rows))

            dmat = xgb.DMatrix(
                win_X.values.astype(np.float32), feature_names=self.feature_names_
            )
            preds_log = self.booster_.predict(dmat)
            preds = np.maximum(np.expm1(preds_log), 0.0)

            for orig_idx, pred in zip(win_rows["_orig_idx"].values, preds):
                result[int(orig_idx)] = pred

            # Заполняем предсказания в extended_history (для rolling features)
            # но с весом 1.0 (полная замена) — drift минимизирован короткими окнами
            win_rows_filled = win_rows.copy()
            win_rows_filled["boardings"] = preds
            extended_history = pd.concat(
                [extended_history, win_rows_filled], ignore_index=True
            )

        return result

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
