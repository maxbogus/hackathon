"""Метрики для оценки качества прогнозов пассажиропотока.

RMSLE — primary (count data, правый хвост).
MAE — для диспетчера (люди, не логарифмы).
MAPE — процент ошибки (исключает y_true == 0 для устойчивости).

Используется в:
- ml/transit_ai/training/evaluate.py (T-035) — production eval pipeline
- ml/transit_ai/benchmark/runner.py (T-038) — offline benchmark
- ml/transit_ai/reports/plots.py (T-037, будущее) — графики

Раньше метрики жили в benchmark/runner.py — теперь вынесены в общий модуль (DRY).
"""
from __future__ import annotations

import numpy as np

__all__ = ["compute_metrics", "mae", "mape", "rmsle"]


def rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Log Error.

    Устойчив к count data с тяжёлым правым хвостом (переполненные вагоны в час пик).
    Negative inputs clipped to 0 (log1p undefined for x < -1).
    """
    y_true = np.maximum(y_true, 0)
    y_pred = np.maximum(y_pred, 0)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error — для диспетчера (люди, не логарифмы)."""
    return float(np.mean(np.abs(y_true - y_pred)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error (%).

    Исключает y_true == 0 строки (избегаем деления на 0).
    Returns 0.0 если все y_true == 0 (guard against empty mask).
    """
    mask = y_true != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Единая точка входа: возвращает все 3 метрики.

    Используется в evaluate_artifact() и benchmark.run_single_benchmark().
    Пустые массивы → нули (no crash).
    """
    if len(y_true) == 0 or len(y_pred) == 0:
        return {"rmsle": 0.0, "mae": 0.0, "mape": 0.0}
    return {
        "rmsle": rmsle(y_true, y_pred),
        "mae": mae(y_true, y_pred),
        "mape": mape(y_true, y_pred),
    }
