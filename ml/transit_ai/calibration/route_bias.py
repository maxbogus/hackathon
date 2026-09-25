"""Per-route bias calibration (T-147, F-020).

Bias correction в log-space: для каждого маршрута считается
median(log1p(actual) - log1p(pred)) на тренировочных данных, и применяется
мультипликативно к предсказаниям как pred_calibrated = pred * exp(bias).

Почему log-space:
- bias симметричен относительно пере-/недо-оценки (bias > 0 → занижали → нужно увеличить)
- стабилен при малых значениях (log1p vs raw division)
- exp(median(log_diff)) = geometric median ratio

Использование:
    from transit_ai.calibration.route_bias import compute_route_bias, apply_route_bias

    biases = compute_route_bias(train["boardings"], train_pred, train["route_id"])
    calibrated = apply_route_bias(test_pred, test_route_ids, biases)

Refs: T-147, F-020
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["apply_route_bias", "compute_route_bias"]


def compute_route_bias(
    train_actual: pd.Series,
    train_pred: pd.Series,
    route_ids: pd.Series,
) -> dict[int, float]:
    """Вычислить per-route bias = median(log1p(actual) - log1p(pred)).

    Args:
        train_actual: фактические значения (boardings) на тренировочной выборке.
        train_pred: предсказания baseline-модели на той же выборке.
        route_ids: route_id для каждой строки.

    Returns:
        {route_id: bias} — bias=0 → нейтральная коррекция (exp(0)=1).
        Routes без записи (cold-start) → bias=0 при применении.

    Raises:
        ValueError: если входные данные пустые.
    """
    if len(train_actual) == 0 or len(train_pred) == 0 or len(route_ids) == 0:
        raise ValueError(
            "Cannot compute route bias on empty training data "
            f"(len actual={len(train_actual)}, pred={len(train_pred)}, "
            f"route_ids={len(route_ids)})"
        )

    df = pd.DataFrame(
        {
            "actual": train_actual.values,
            "pred": train_pred.values,
            "route_id": route_ids.values,
        }
    )
    # Clip к 0 (предсказания могут быть отрицательными, log1p требует >= 0)
    actual_clipped = np.maximum(df["actual"].astype(np.float64), 0.0)
    pred_clipped = np.maximum(df["pred"].astype(np.float64), 0.0)

    df["log_actual"] = np.log1p(actual_clipped)
    df["log_pred"] = np.log1p(pred_clipped)
    df["log_bias"] = df["log_actual"] - df["log_pred"]

    biases = df.groupby("route_id")["log_bias"].median()
    return {int(route_id): float(bias) for route_id, bias in biases.items()}


def apply_route_bias(
    predictions: np.ndarray,
    route_ids: np.ndarray,
    biases: dict[int, float],
) -> np.ndarray:
    """Применить per-route bias мультипликативно: pred_calibrated = pred * exp(bias).

    Args:
        predictions: исходные предсказания baseline-модели.
        route_ids: route_id для каждого предсказания.
        biases: {route_id: bias} из compute_route_bias.

    Returns:
        Новый массив calibrated predictions (>= 0). Входной массив не мутируется.

    Edge case:
        - route_id не в biases → bias=0, коррекция = 1.0 (no change).
        - bias очень отрицательный → exp(bias)≈0 → предсказание ≈ 0 (clipped).
    """
    preds = np.asarray(predictions, dtype=np.float64)
    out = preds.copy()  # defensive copy

    for i, r in enumerate(route_ids):
        bias = biases.get(int(r), 0.0)
        out[i] = preds[i] * np.exp(bias)

    return np.maximum(out, 0.0)  # не уходим в отрицательные
