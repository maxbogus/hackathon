"""Predictor base class (ABC).

Все ML модели (BaselineMean, XGBoost, GRU, Hybrid) наследуются от Predictor.
Контракт: см. `.clinerules/08-contracts-and-artifacts.md`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True, slots=True)
class PredictionPoint:
    """Один временной слот прогноза."""

    period_start: datetime
    period_end: datetime
    value: float
    lower: float
    upper: float
    stop_id: int
    route_id: int | None = None
    model_id: str | None = None


class Predictor(ABC):
    """Abstract base for all ML predictors.

    Lifecycle: `fit(df) -> predict(...) -> save(path) -> load(path)`.
    The `predict()` method takes a single stop_id and a time range, returns a
    list of PredictionPoints (one per hour inside the range).
    """

    model_id: str = "base"
    kind: str = "base"

    @abstractmethod
    def fit(self, ridership: pd.DataFrame) -> None:
        """Train on historical ridership data."""
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        stop_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> list[PredictionPoint]:
        """Predict ridership for one stop in [period_start, period_end]."""
        raise NotImplementedError

    @abstractmethod
    def save(self, path: str) -> None:
        """Persist model + metadata to disk."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> Predictor:
        """Restore from disk."""
        raise NotImplementedError


__all__ = ["PredictionPoint", "Predictor"]
