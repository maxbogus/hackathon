"""Plotting helpers for ML metrics + predictions (T-037).

Each function returns Path to a PNG file (headless Agg backend).

Используется в:
- ml/transit_ai/training/evaluate.py — после evaluate_artifact
- ml/scripts/evaluate.py — make evaluate пишет ≥1 PNG
- ml/transit_ai/benchmark/report.py — leaderboard (T-038+)

Зависимости:
- matplotlib ≥ 3.5 (headless Agg backend)
- numpy / pandas

Использует transit_ai.reports.metrics как single source of truth (D-006).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless backend для CI и remote-серверов

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import ArrayLike

logger = logging.getLogger("plots")

PLOTS_VERSION = "0.1.0"

#: Hard limits из clinerule 19-ml-benchmark-pipeline.md / training/evaluate.py.
DEFAULT_THRESHOLDS: dict[str, float] = {
    "rmsle": 0.5,
    "mae": 15.0,
    "mape": 25.0,
}


def _default_rcparams() -> None:
    """Apply consistent style for all plots."""
    plt.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.figsize": (8.0, 5.0),
        }
    )


def _ensure_output_dir(output: Path) -> Path:
    """Create parent dir if missing; return absolute Path."""
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _save_or_empty(ax: Any, output: Path, *, kind: str) -> Path:
    """Save figure; raise if nothing produced."""
    output = _ensure_output_dir(output)
    try:
        ax.figure.savefig(output, bbox_inches="tight")
    finally:
        plt.close(ax.figure)
    if not output.exists() or output.stat().st_size < 100:
        raise RuntimeError(f"Plot {kind!r} produced empty file at {output}")
    logger.info(f"✅ Wrote {kind!r} plot → {output} ({output.stat().st_size} bytes)")
    return output


def _empty_plot(output: Path, msg: str = "no data") -> Path:
    """Save a placeholder PNG saying there's nothing to plot."""
    output = _ensure_output_dir(output)
    _default_rcparams()
    _fig, ax = plt.subplots(figsize=(6.0, 3.0))
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=14, color="gray")
    ax.set_axis_off()
    return _save_or_empty(ax, output, kind="empty")


# ---------- plot_metrics ----------


def plot_metrics(
    metrics: Mapping[str, float],
    output: Path,
    *,
    show_thresholds: bool = True,
    thresholds: Mapping[str, float] | None = None,
) -> Path:
    """Bar chart RMSLE/MAE/MAPE + threshold lines.

    Args:
        metrics: {"rmsle": 0.42, "mae": 12.3, "mape": 18.0}
        output: путь к PNG
        show_thresholds: рисовать ли горизонтальные пороги
        thresholds: {"rmsle": 0.5, ...} — default = DEFAULT_THRESHOLDS
    """
    output = _ensure_output_dir(output)
    _default_rcparams()

    if not metrics:
        return _empty_plot(output, "no metrics")

    keys = list(metrics.keys())
    values = [float(metrics[k]) for k in keys]
    _fig, ax = plt.subplots(figsize=(7.0, 4.0))
    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"][: len(keys)]
    ax.bar(keys, values, color=colors)

    if show_thresholds:
        thr = dict(thresholds or DEFAULT_THRESHOLDS)
        for i, k in enumerate(keys):
            if k in thr:
                ax.hlines(
                    thr[k], i - 0.4, i + 0.4, colors="red", linestyles="--", linewidth=1
                )
                ax.text(
                    i,
                    thr[k] * 1.05,
                    f"thr={thr[k]}",
                    ha="center",
                    fontsize=8,
                    color="red",
                )

    ax.set_ylabel("Value")
    ax.set_title("Metrics vs Thresholds")
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=9)
    return _save_or_empty(ax, output, kind="metrics")


# ---------- plot_predictions_vs_actual ----------


def plot_predictions_vs_actual(
    y_true: ArrayLike,
    y_pred: ArrayLike,
    output: Path,
    *,
    max_points: int = 1000,
) -> Path:
    """Scatter: y_true vs y_pred + y=x reference line."""
    output = _ensure_output_dir(output)
    _default_rcparams()

    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    if y_true_arr.size == 0 or y_pred_arr.size == 0:
        return _empty_plot(output, "no predictions")

    # Subsample if too large
    n = y_true_arr.size
    if n > max_points:
        rng = np.random.default_rng(42)
        idx = rng.choice(n, size=max_points, replace=False)
        y_true_arr = y_true_arr[idx]
        y_pred_arr = y_pred_arr[idx]

    _fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.scatter(y_true_arr, y_pred_arr, alpha=0.4, s=10, color="#2E86AB")
    lo = min(float(y_true_arr.min()), float(y_pred_arr.min()))
    hi = max(float(y_true_arr.max()), float(y_pred_arr.max()))
    ax.plot([lo, hi], [lo, hi], "r--", linewidth=1, label="y = x")

    # Compute % within ±20% of actual
    mask = y_true_arr > 0
    if mask.any():
        ratio = np.abs(y_pred_arr[mask] - y_true_arr[mask]) / np.maximum(
            y_true_arr[mask], 1e-6
        )
        within_20pct = float((ratio <= 0.20).mean() * 100)
    else:
        within_20pct = float("nan")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title(
        f"Predictions vs Actual ({n} points"
        + (f", {max_points} sampled" if n > max_points else "")
        + f", {within_20pct:.1f}% within ±20%)"
    )
    ax.legend()
    return _save_or_empty(ax, output, kind="predictions_vs_actual")


# ---------- plot_calibration_biases ----------


def plot_calibration_biases(
    calibration: Mapping[str, Any] | Path | str,
    output: Path,
) -> Path:
    """Histogram per-bucket bias + global bias vertical line."""
    output = _ensure_output_dir(output)
    _default_rcparams()

    if isinstance(calibration, (str, Path)):
        calibration = json.loads(Path(calibration).read_text(encoding="utf-8"))

    calib_dict: Mapping[str, Any] = (
        calibration if isinstance(calibration, Mapping) else {}
    )
    biases = calib_dict.get("biases", [])
    global_bias = float(calib_dict.get("global_bias", 0.0))

    if not biases:
        return _empty_plot(output, "no bias buckets")

    _fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.hist(
        biases, bins=min(20, len(biases)), color="#A23B72", edgecolor="black", alpha=0.7
    )
    ax.axvline(
        global_bias,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"global={global_bias:.4f}",
    )
    ax.axvline(0.0, color="black", linewidth=0.5)
    ax.set_xlabel("Per-bucket bias (log-space)")
    ax.set_ylabel("Count")
    ax.set_title(
        f"Calibration Biases (kind={calib_dict.get('kind', '?')}, {len(biases)} buckets)"
    )
    ax.legend()
    return _save_or_empty(ax, output, kind="calibration_biases")


# ---------- plot_residuals ----------


def plot_residuals(
    y_true: ArrayLike,
    y_pred: ArrayLike,
    output: Path,
) -> Path:
    """Residuals (y_true - y_pred) histogram + scatter vs predicted."""
    output = _ensure_output_dir(output)
    _default_rcparams()

    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    if y_true_arr.size == 0 or y_pred_arr.size == 0:
        return _empty_plot(output, "no residuals")

    residuals = y_true_arr - y_pred_arr
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.0))

    ax1.hist(residuals, bins=30, color="#F18F01", edgecolor="black", alpha=0.7)
    ax1.set_xlabel("Residual (y_true - y_pred)")
    ax1.set_ylabel("Count")
    ax1.set_title(f"Residuals (mean={residuals.mean():.2f}, std={residuals.std():.2f})")
    ax1.axvline(0, color="red", linestyle="--", linewidth=1)

    ax2.scatter(y_pred_arr, residuals, alpha=0.4, s=10, color="#2E86AB")
    ax2.axhline(0, color="red", linestyle="--", linewidth=1)
    ax2.set_xlabel("Predicted")
    ax2.set_ylabel("Residual")
    ax2.set_title("Residuals vs Predicted")

    fig.tight_layout()
    output = _ensure_output_dir(output)
    try:
        fig.savefig(output, bbox_inches="tight")
    finally:
        plt.close(fig)
    logger.info(f"✅ Wrote residuals plot → {output}")
    return output


__all__ = [
    "DEFAULT_THRESHOLDS",
    "PLOTS_VERSION",
    "plot_calibration_biases",
    "plot_metrics",
    "plot_predictions_vs_actual",
    "plot_residuals",
]
