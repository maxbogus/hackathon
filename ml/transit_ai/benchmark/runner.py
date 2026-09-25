"""Walk-forward CV runner + run_benchmark entry point.

Source: contest/ecup26-user-value/scripts/benchmark_t3.py (адаптация под Transit-AI).

Walk-forward (не train_test_split!) — обязательно для timeseries, иначе утечка будущего.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from transit_ai.benchmark.configs import BenchmarkConfig, BenchmarkResult
from transit_ai.reports.metrics import mae, mape, rmsle

logger = logging.getLogger("benchmark.runner")


@dataclass
class FoldSplit:
    """One walk-forward fold: train_end / val_start / val_end."""

    fold_idx: int
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp


def walk_forward_splits(
    dates: pd.DatetimeIndex,
    n_folds: int,
) -> list[FoldSplit]:
    """Генерирует walk-forward folds с равными интервалами.

    Пример для n_folds=4 с dates от 2024-01-01 до 2026-09-20:
    - fold 1: train до 2024-08-05, val 2024-08-05 — 2025-03-10
    - fold 2: train до 2025-03-10, val 2025-03-10 — 2025-10-13
    - ...
    """
    if n_folds < 2:
        raise ValueError(f"n_folds must be >= 2 (got {n_folds})")
    if len(dates) < n_folds + 1:
        raise ValueError(f"dates too short for {n_folds} folds")

    min_date, max_date = dates.min(), dates.max()
    total_span = max_date - min_date
    chunk = total_span // (n_folds + 1)

    splits: list[FoldSplit] = []
    for i in range(1, n_folds + 1):
        train_end = min_date + chunk * i
        val_start = train_end
        val_end = train_end + chunk
        splits.append(
            FoldSplit(
                fold_idx=i, train_end=train_end, val_start=val_start, val_end=val_end
            )
        )
    return splits


# Метрики импортированы из transit_ai.reports.metrics (T-035: единый источник правды).


def run_single_benchmark(
    config: BenchmarkConfig,
    data: pd.DataFrame,
    target_col: str = "value",
    date_col: str = "date",
) -> BenchmarkResult:
    """Запустить один benchmark: walk-forward CV + метрики.

    Args:
        config: BenchmarkConfig с model_id и hyperparams.
        data: DataFrame с колонками date_col, target_col + features.
        target_col: имя колонки с y (count of passengers).
        date_col: имя колонки с timestamp.

    Returns:
        BenchmarkResult с per-fold scores + агрегированными метриками.

    Note:
        Это заглушка — реальные модели подключатся в T-027..T-030.
        Сейчас возвращает synthetic scores на основе mean prediction.
    """
    logger.info(
        f"Running benchmark: {config.model_id} (config_hash={config.config_hash()})"
    )
    start = time.time()

    dates = pd.DatetimeIndex(data[date_col])
    splits = walk_forward_splits(dates, config.cv_folds)

    fold_scores: list[float] = []
    for fold in splits:
        train_mask = data[date_col] <= fold.train_end
        val_mask = (data[date_col] > fold.val_start) & (data[date_col] <= fold.val_end)
        if train_mask.sum() == 0 or val_mask.sum() == 0:
            logger.warning(f"Fold {fold.fold_idx}: empty split, skipping")
            continue
        train_mean = data.loc[train_mask, target_col].mean()
        val_pred = np.full(val_mask.sum(), train_mean)
        val_true = data.loc[val_mask, target_col].values
        fold_scores.append(rmsle(val_true, val_pred))

    # Aggregate metrics (placeholder — реальные модели дадут честные цифры)
    metrics = {
        "rmsle": float(np.mean(fold_scores)) if fold_scores else 0.0,
        "mae": mae(val_true, val_pred) if fold_scores else 0.0,  # last fold
        "mape": mape(val_true, val_pred) if fold_scores else 0.0,
    }

    elapsed = time.time() - start

    return BenchmarkResult(
        config=config,
        metrics=metrics,
        fold_scores=fold_scores,
        train_time_sec=elapsed,
        git_commit="unknown",  # будет заполнено в cli.py
        train_data_hash="unknown",
        timestamp=datetime.now(UTC).isoformat(),
        notes="BaselineMean placeholder (T-038 in progress)",
    )
