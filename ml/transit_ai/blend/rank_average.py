"""Ensemble blender (T-173): rank-average или weighted-mean.

T-173 выявил что rank-average **сглаживает** пики и снижает WAPE-score
(с 0.90 → 0.71) для count data с сильными пиками (час пик). Weighted-mean
с весами, пропорциональными обратной ошибке на holdout, оказался лучше.

API:
- rank_average_blend(predictions, scale_target_mean=None)
- weighted_mean_blend(predictions, weights=None)

Использование:
    from transit_ai.blend.rank_average import rank_average_blend, weighted_mean_blend
"""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata

__all__ = ["rank_average_blend", "weighted_mean_blend"]


def rank_average_blend(
    predictions: list[np.ndarray],
    scale_target_mean: float | None = None,
) -> np.ndarray:
    """Rank-average ensemble (по evehicle_pred/scripts/blend.py).

    Алгоритм:
        1. rankdata для каждого массива (средний ранг для тай-брейков)
        2. Усреднить ранги
        3. Нормировать в [0, 1]
        4. Rescale к mean первой модели (или к scale_target_mean)

    ⚠️ На count data с сильными пиками (час пик) rank-average может СГЛАЖИВАТЬ
    пики и ухудшать WAPE-score. Для нашей задачи лучше weighted_mean_blend.

    Args:
        predictions: список 1D массивов одинаковой длины.
        scale_target_mean: целевое среднее для rescale (default=mean первой модели).

    Returns:
        np.ndarray той же длины.
    """
    if not predictions:
        raise ValueError("predictions list is empty")
    n = len(predictions[0])
    if n == 0:
        return np.array([], dtype=np.float64)
    for i, p in enumerate(predictions):
        if len(p) != n:
            raise ValueError(
                "predictions[" + str(i) + "] length " + str(len(p)) + " != predictions[0] length " + str(n)
            )

    ranks_stack = np.stack([rankdata(p, method="average") for p in predictions])
    mean_ranks = ranks_stack.mean(axis=0)

    rank_min = mean_ranks.min()
    rank_max = mean_ranks.max()
    if rank_max == rank_min:
        return np.full(n, predictions[0].mean(), dtype=np.float64)

    norm_ranks = (mean_ranks - rank_min) / (rank_max - rank_min)
    target_mean = scale_target_mean if scale_target_mean is not None else float(predictions[0].mean())
    scale = target_mean / max(norm_ranks.mean(), 1e-9)
    return (norm_ranks * scale).astype(np.float64)


def weighted_mean_blend(
    predictions: list[np.ndarray],
    weights: list[float] | None = None,
) -> np.ndarray:
    """Weighted mean ensemble — сохраняет абсолютные значения.

    Используется для count data (пасcажиропоток), где rank-average сглаживает
    пики. Weighted mean в обычном пространстве — простой и стабильный ансамбль.

    Args:
        predictions: список 1D массивов одинаковой длины.
        weights: список весов (default=равные веса).

    Returns:
        np.ndarray взвешенного среднего.

    Raises:
        ValueError: если массивы разной длины или список пуст.
    """
    if not predictions:
        raise ValueError("predictions list is empty")
    n = len(predictions[0])
    if n == 0:
        return np.array([], dtype=np.float64)
    for i, p in enumerate(predictions):
        if len(p) != n:
            raise ValueError(
                "predictions[" + str(i) + "] length " + str(len(p)) + " != predictions[0] length " + str(n)
            )

    if weights is None:
        weights = [1.0 / len(predictions)] * len(predictions)
    if len(weights) != len(predictions):
        raise ValueError(
            f"weights length {len(weights)} != predictions length {len(predictions)}"
        )
    w = np.asarray(weights, dtype=np.float64)
    w = w / w.sum()  # normalize to sum=1
    result = np.zeros(len(predictions[0]), dtype=np.float64)
    for i in range(len(predictions)):
        result += w[i] * predictions[i].astype(np.float64)
    return result
