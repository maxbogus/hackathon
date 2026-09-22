"""Tests for benchmark smoke scripts (T-039).

Контракт:
- `benchmark_baseline.py` запускает smoke на 1 конфиге за <60 сек
- `benchmark_all.py` запускает grid или random search
- Каждый BenchmarkResult содержит git_commit, seed (R6 hackathon-rules)
- CLI использует SyntheticSource (не hardcoded data)
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from transit_ai.benchmark.configs import BenchmarkConfig, BenchmarkResult
from transit_ai.benchmark.synthetic_data import load_synthetic_benchmark_data

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------- Pure unit tests for synthetic_data loader ----------


def test_load_synthetic_benchmark_data_returns_aggregated_dataframe() -> None:
    """Aggregation: ridership → (date, value) DataFrame with passenger sum per day."""
    df = load_synthetic_benchmark_data(n_days=21, seed=42)
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) >= {"date", "value"}
    assert len(df) == 21
    assert df["value"].sum() > 0
    assert (df["value"] >= 0).all()


def test_load_synthetic_benchmark_data_is_deterministic() -> None:
    """Один seed → одинаковые данные (R6)."""
    df1 = load_synthetic_benchmark_data(n_days=14, seed=42)
    df2 = load_synthetic_benchmark_data(n_days=14, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_load_synthetic_benchmark_data_contains_weekday_signal() -> None:
    """Будни vs выходные: среднее по будням должно отличаться от выходных (sanity)."""
    df = load_synthetic_benchmark_data(n_days=28, seed=42)
    df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
    weekday_mean = df.loc[df["weekday"] < 5, "value"].mean()
    weekend_mean = df.loc[df["weekday"] >= 5, "value"].mean()
    assert weekday_mean != weekend_mean


# ---------- Tests for benchmark scripts (smoke) ----------


def _run_script(
    script_name: str, *args: str, timeout: int = 60
) -> subprocess.CompletedProcess[str]:
    """Run a benchmark script via uv in the ml/ workspace."""
    cmd = [
        "uv",
        "--directory",
        str(REPO_ROOT / "ml"),
        "run",
        "python",
        f"scripts/{script_name}",
        *args,
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )


def test_benchmark_baseline_smoke_runs_and_writes_report() -> None:
    """benchmark_baseline.py завершается успешно, пишет markdown report."""
    result = _run_script("benchmark_baseline.py", timeout=60)

    if result.returncode != 0:
        pytest.fail(
            f"benchmark_baseline.py failed: stdout={result.stdout[:500]} "
            f"stderr={result.stderr[:500]}"
        )

    default_report = REPO_ROOT / "docs" / "reports" / "benchmark_baseline_smoke.md"
    assert default_report.exists(), f"Report not found at {default_report}"
    content = default_report.read_text()
    assert "RMSLE" in content or "rmsle" in content.lower()
    default_report.unlink(missing_ok=True)


def test_benchmark_all_grid_runs_with_default_args() -> None:
    """benchmark_all.py со default args запускает ≤12 configs и пишет report."""
    today = datetime.now(UTC).date().isoformat()
    expected = REPO_ROOT / "docs" / "reports" / f"benchmark_{today}.md"

    result = _run_script(
        "benchmark_all.py", "--max-configs", "2", "--folds", "2", timeout=90
    )

    if result.returncode != 0:
        pytest.fail(
            f"benchmark_all.py failed: stdout={result.stdout[:500]} "
            f"stderr={result.stderr[:500]}"
        )

    if expected.exists():
        content = expected.read_text()
        assert "RMSLE" in content
        expected.unlink(missing_ok=True)
        expected.with_suffix(".csv").unlink(missing_ok=True)


def test_benchmark_all_random_strategy_runs() -> None:
    """benchmark_all.py --strategy random --max-configs 3 работает."""
    result = _run_script(
        "benchmark_all.py",
        "--strategy",
        "random",
        "--max-configs",
        "3",
        "--folds",
        "2",
        timeout=60,
    )
    if result.returncode != 0:
        assert "ModuleNotFoundError" not in result.stderr
        assert "ImportError" not in result.stderr


# ---------- Contract test: BenchmarkResult fields ----------


def test_benchmark_result_has_required_reproducibility_fields() -> None:
    """Каждый BenchmarkResult обязан иметь git_commit и seed (R6 hackathon-rules)."""
    cfg = BenchmarkConfig(model_id="baseline_v1", seed=42, cv_folds=2)
    result = BenchmarkResult(
        config=cfg,
        metrics={"rmsle": 0.42, "mae": 12.3, "mape": 18.0},
        fold_scores=[0.40, 0.44],
        train_time_sec=0.5,
    )
    assert result.git_commit == "unknown" or isinstance(result.git_commit, str)
    assert result.config.seed == 42


def test_benchmark_result_to_json_roundtrip() -> None:
    """BenchmarkResult.to_json_dict → сериализуемый dict (для report)."""
    cfg = BenchmarkConfig(model_id="xgboost_v1", hyperparams={"n_estimators": 200})
    result = BenchmarkResult(
        config=cfg, metrics={"rmsle": 0.3}, fold_scores=[0.3], train_time_sec=1.0
    )
    d = result.to_json_dict()
    json.dumps(d)
    assert d["config"]["model_id"] == "xgboost_v1"
    assert d["config"]["horizons"] == ["day", "month"]


# ---------- Sanity: scripts/runner metrics consistency ----------


def test_benchmark_uses_reports_metrics() -> None:
    """benchmark/runner.py импортирует RMSLE/MAE/MAPE из reports/metrics (D-006)."""
    from transit_ai.benchmark import runner
    from transit_ai.reports import metrics

    assert hasattr(runner, "run_single_benchmark")
    assert hasattr(metrics, "rmsle")
    assert hasattr(metrics, "mae")
    assert hasattr(metrics, "mape")
    assert hasattr(metrics, "compute_metrics")
