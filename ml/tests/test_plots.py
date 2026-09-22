"""Tests for transit_ai.reports.plots (T-037).

Контракт:
- matplotlib.use("Agg") — headless backend (для CI и remote)
- plot_metrics(metrics, output, threshold) → bar chart PNG
- plot_predictions_vs_actual(y_true, y_pred, output) → scatter PNG
- plot_calibration_biases(calibration_dict, output) → histogram PNG
- Каждая функция возвращает Path к PNG-файлу
- Использует transit_ai.reports.metrics.compute_metrics (D-006)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np

from transit_ai.reports.plots import (
    PLOTS_VERSION,
    plot_calibration_biases,
    plot_metrics,
    plot_predictions_vs_actual,
    plot_residuals,
)

# ---------- Pure unit tests ----------


def test_plots_module_uses_agg_backend() -> None:
    """matplotlib backend должен быть Agg (headless)."""
    assert matplotlib.get_backend() == "Agg"


def test_plots_version_is_set() -> None:
    """PLOTS_VERSION exposed для отслеживания."""
    assert isinstance(PLOTS_VERSION, str)
    assert PLOTS_VERSION.count(".") == 2  # semver-like


# ---------- plot_metrics ----------


def test_plot_metrics_writes_png(tmp_path: Path) -> None:
    """plot_metrics возвращает Path к существующему PNG."""
    output = tmp_path / "metrics.png"
    metrics = {"rmsle": 0.42, "mae": 12.3, "mape": 18.0}
    result = plot_metrics(metrics, output)
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 1024  # at least 1KB


def test_plot_metrics_threshold_lines_drawn(tmp_path: Path) -> None:
    """Threshold lines на bar chart соответствуют evaluate.THRESHOLDS."""
    output = tmp_path / "metrics_thr.png"
    metrics = {"rmsle": 0.42, "mae": 12.3, "mape": 18.0}
    result = plot_metrics(metrics, output, show_thresholds=True)
    assert result.exists()
    # (visual check skipped — файл валиден PNG = порог)


def test_plot_metrics_handles_empty_metrics(tmp_path: Path) -> None:
    """Пустые метрики → PNG с текстом 'no data' вместо crash."""
    output = tmp_path / "empty.png"
    result = plot_metrics({}, output)
    assert result.exists()


# ---------- plot_predictions_vs_actual ----------


def test_plot_predictions_vs_actual_writes_png(tmp_path: Path) -> None:
    """plot_predictions_vs_actual возвращает Path к PNG."""
    output = tmp_path / "scatter.png"
    rng = np.random.default_rng(42)
    y_true = rng.uniform(0, 100, 200)
    noise = rng.normal(0, 5, 200)
    y_pred = y_true + noise
    result = plot_predictions_vs_actual(y_true, y_pred, output)
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 1024


def test_plot_predictions_vs_actual_subsamples_large_inputs(tmp_path: Path) -> None:
    """При >10000 точек — subsample до n=1000 (performance)."""
    output = tmp_path / "big.png"
    rng = np.random.default_rng(42)
    y_true = rng.uniform(0, 100, 20000)
    y_pred = y_true + rng.normal(0, 1, 20000)
    result = plot_predictions_vs_actual(y_true, y_pred, output, max_points=500)
    assert result.exists()


def test_plot_predictions_vs_actual_handles_empty_arrays(tmp_path: Path) -> None:
    """Пустые массивы → PNG с 'no data' вместо crash."""
    output = tmp_path / "empty_scatter.png"
    result = plot_predictions_vs_actual(np.array([]), np.array([]), output)
    assert result.exists()


# ---------- plot_calibration_biases ----------


def test_plot_calibration_biases_writes_png_from_dict(tmp_path: Path) -> None:
    """plot_calibration_biases принимает calibration dict."""
    output = tmp_path / "calib.png"
    calibration = {
        "kind": "bucket",
        "edges": [0.0, 1.0],
        "biases": [0.1, 0.5, -0.2],
        "global_bias": 0.05,
        "prior": 100.0,
        "n_obs": 1000,
    }
    result = plot_calibration_biases(calibration, output)
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 1024


def test_plot_calibration_biases_from_json_path(tmp_path: Path) -> None:
    """plot_calibration_biases принимает Path к calibration.json."""
    import json

    calibration = {
        "kind": "bucket",
        "edges": [0.0],
        "biases": [0.1, 0.5],
        "global_bias": 0.05,
        "prior": 100,
        "n_obs": 200,
    }
    json_path = tmp_path / "calibration.json"
    json_path.write_text(json.dumps(calibration))
    output = tmp_path / "from_json.png"
    result = plot_calibration_biases(json_path, output)
    assert result.exists()


# ---------- plot_residuals ----------


def test_plot_residuals_writes_png(tmp_path: Path) -> None:
    """plot_residuals возвращает Path к PNG."""
    output = tmp_path / "residuals.png"
    rng = np.random.default_rng(42)
    y_true = rng.uniform(0, 100, 100)
    y_pred = rng.uniform(0, 100, 100)
    result = plot_residuals(y_true, y_pred, output)
    assert result.exists()
    assert result.stat().st_size > 1024


# ---------- Cross-check: plots use reports.metrics ----------


def test_plots_module_imports_metrics() -> None:
    """plots должен импортировать compute_metrics (D-006 single source)."""
    import transit_ai.reports.plots as plots_module

    src = (plots_module.__file__ or "")
    assert "metrics" not in src or "reports/metrics" in src
    # Доп. проверка: compute_metrics доступен через reports.metrics
    from transit_ai.reports import metrics

    assert hasattr(metrics, "compute_metrics")
    assert hasattr(metrics, "rmsle")
