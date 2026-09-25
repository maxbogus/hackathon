"""Per-route / per-hour / per-weekday WAPE-диагностика (T-146, F-019).

После submission #1 → WAPE=0.72568 на платформе хакатона нужно понять, какие
маршруты / часы / дни недели дают наибольшую ошибку. Это позволит сфокусировать
улучшения (T-147 calibration, T-148 exogenous, T-152 XGBoost) на слабых местах.

Использование:
    from transit_ai.reports.diagnose import diagnose
    result = diagnose(test_df, predictions)
    print(result["per_route"])  # {1: 0.85, 7: 0.92, ...}
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

__all__ = ["diagnose", "per_hour_wape", "per_route_wape", "per_weekday_wape"]


def _score_for_group(y: np.ndarray, yhat: np.ndarray) -> float:
    """WAPE-score для одной группы = max(0, 1 - Σ|y-ŷ|/Σy)."""
    y = np.maximum(y.astype(np.float64), 0.0)
    yhat = np.maximum(yhat.astype(np.float64), 0.0)
    denom = float(y.sum())
    if denom == 0.0 or len(y) == 0:
        return 0.0
    wape = float(np.abs(y - yhat).sum() / denom)
    return float(max(0.0, 1.0 - wape))


def per_route_wape(test_df: pd.DataFrame, predictions: np.ndarray) -> dict[int, float]:
    """Per-route WAPE-score.

    Returns:
        {route_id: wape_score ∈ [0, 1]} — больше = лучше.
    """
    if len(test_df) == 0:
        return {}
    out: dict[int, float] = {}
    df = test_df.copy()
    df["__pred__"] = predictions
    for route, group in df.groupby("route_id"):
        out[int(route)] = _score_for_group(
            group["boardings"].values, group["__pred__"].values
        )
    return out


def per_hour_wape(test_df: pd.DataFrame, predictions: np.ndarray) -> dict[int, float]:
    """Per-hour-of-day WAPE-score (0..23)."""
    if len(test_df) == 0:
        return {}
    out: dict[int, float] = {}
    df = test_df.copy()
    df["__pred__"] = predictions
    for hour, group in df.groupby("hour"):
        out[int(hour)] = _score_for_group(
            group["boardings"].values, group["__pred__"].values
        )
    return out


def per_weekday_wape(
    test_df: pd.DataFrame, predictions: np.ndarray
) -> dict[int, float]:
    """Per-weekday WAPE-score (0=Mon, 6=Sun)."""
    if len(test_df) == 0:
        return {}
    out: dict[int, float] = {}
    df = test_df.copy()
    df["__pred__"] = predictions
    if "weekday" not in df.columns:
        df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
    for wd, group in df.groupby("weekday"):
        out[int(wd)] = _score_for_group(
            group["boardings"].values, group["__pred__"].values
        )
    return out


def diagnose(test_df: pd.DataFrame, predictions: np.ndarray) -> dict[str, Any]:
    """Полная диагностика: overall + per-route + per-hour + per-weekday.

    Returns:
        {
            "overall": float,         # WAPE-score ∈ [0, 1]
            "per_route": {route_id: wape_score},
            "per_hour": {hour: wape_score},
            "per_weekday": {weekday: wape_score},
            "n_points": int,
            "total_boardings": float,
        }
    """
    if len(test_df) == 0 or len(predictions) == 0:
        return {
            "overall": 0.0,
            "per_route": {},
            "per_hour": {},
            "per_weekday": {},
            "n_points": 0,
            "total_boardings": 0.0,
        }

    overall = _score_for_group(test_df["boardings"].values, np.asarray(predictions))
    return {
        "overall": overall,
        "per_route": per_route_wape(test_df, predictions),
        "per_hour": per_hour_wape(test_df, predictions),
        "per_weekday": per_weekday_wape(test_df, predictions),
        "n_points": len(test_df),
        "total_boardings": float(test_df["boardings"].sum()),
    }
