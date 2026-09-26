"""CatBoost route-level predictor (T-173).

Тот же интерфейс, что и XGBoostRoutePredictor:
- fit(ridership) — обучает один CatBoostRegressor
- predict_batch(df, lag_lookup) — median predictions
- predict_recursive(history, future_grid) — rolling-window forecast

Переиспользует _make_features и FEATURE_NAMES из xgboost_route.py,
чтобы фичи (включая events T-172) были идентичны.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from transit_ai.models.xgboost_route import FEATURE_NAMES, _make_features

__all__ = ["CatBoostRoutePredictor"]

# Lazy import — catboost тяжёлый, грузим только при первом использовании
_catboost: Any = None


def _get_catboost() -> Any:
    """Lazy import catboost.CatBoostRegressor (избегаем overhead на старте)."""
    global _catboost
    if _catboost is None:
        from catboost import CatBoostRegressor

        _catboost = CatBoostRegressor
    return _catboost


@dataclass
class CatBoostRoutePredictor:
    """CatBoost predictor для route-level данных (T-173).

    Обучает один CatBoostRegressor (median, RMSE loss).
    Гиперпараметры по умолчанию взяты из evehicle_pred/scripts/train_cat.py.
    """

    model_id: str = "catboost_v1"
    kind: str = "catboost_route"

    iterations: int = 300
    depth: int = 6
    learning_rate: float = 0.05
    random_seed: int = 42

    # Fitted state
    model_: Any = None  # catboost.CatBoostRegressor
    feature_names_: list[str] = field(default_factory=list)
    fitted_: bool = False

    def fit(self, ridership: pd.DataFrame) -> None:
        """Train CatBoostRegressor на route-level данных.

        ridership должен содержать: [timestamp, route_id, date, hour, boardings].
        Полный ряд (train + holdout) для корректных lag features.
        """
        if ridership.empty:
            raise ValueError("Cannot fit CatBoostRoutePredictor on empty data")
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

        CatBoostRegressor = _get_catboost()
        self.model_ = CatBoostRegressor(
            iterations=self.iterations,
            depth=self.depth,
            learning_rate=self.learning_rate,
            random_seed=self.random_seed,
            loss_function="RMSE",
            verbose=0,
            allow_writing_files=False,
        )
        # CatBoost на log1p(target) — стабилизирует variance для count data
        self.model_.fit(
            X.values.astype(np.float32),
            np.log1p(y.values.astype(np.float32)),
        )
        self.fitted_ = True

    def predict_batch(
        self,
        df: pd.DataFrame,
        lag_lookup: dict[tuple[int, int, int], float] | None = None,
    ) -> np.ndarray:
        """Predict для batch of (route, date, hour).

        df должен содержать [route_id, date, hour] (timestamp вычислим).
        lag_lookup (T-152-fallback): dict[(route, weekday, hour)] -> mean boardings
        из train данных. Используется если df не содержит boardings.
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
        preds_log = self.model_.predict(X.values.astype(np.float32))
        preds = np.expm1(preds_log)
        return np.maximum(preds, 0.0)

    def save(self, path: Path | str) -> None:
        """Сохранить модель в .pkl через pickle (по образцу xgboost)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path | str) -> CatBoostRoutePredictor:
        """Загрузить модель из .pkl."""
        p = Path(path)
        with p.open("rb") as f:
            return pickle.load(f)
