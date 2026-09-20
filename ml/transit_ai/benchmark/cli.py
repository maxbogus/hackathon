"""argparse CLI for benchmark pipeline.

Запускается из scripts/run_benchmark.py.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from transit_ai.benchmark.configs import BenchmarkConfig, BenchmarkResult, PRESET_CONFIGS
from transit_ai.benchmark.runner import run_single_benchmark as run_one

logger = logging.getLogger("benchmark.cli")


def _git_commit() -> str:
    """Get current short git commit, or 'unknown' if not a git repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parents[3],
        ).decode().strip()
    except Exception:
        return "unknown"


def _synthetic_data(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic passenger flow data for benchmark smoke test.

    Будет заменён на RealSource в T-026.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    # Synthetic: 100 ± 30 пассажиров + weekly seasonality + noise
    weekday = dates.dayofweek
    seasonal = 30 * np.sin(weekday * np.pi / 3.5)
    values = np.maximum(rng.normal(100 + seasonal, 15), 0)
    return pd.DataFrame({"date": dates, "value": values})


def run_benchmark_sweep(
    strategy: str,
    max_configs: int,
    output: Path,
    seed: int,
    folds: int,
) -> int:
    """CLI entry: run grid or random search + write report."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Select configs based on strategy
    if strategy == "grid":
        configs = PRESET_CONFIGS[:max_configs]
    else:  # random
        import random
        rng = random.Random(seed)
        all_hp = [
            {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05},
            {"n_estimators": 500, "max_depth": 8, "learning_rate": 0.03},
            {"n_estimators": 1000, "max_depth": 10, "learning_rate": 0.01},
        ]
        model_ids = ["baseline_v1", "xgboost_v1", "gru_v1"]
        configs = [
            BenchmarkConfig(
                model_id=rng.choice(model_ids),
                feature_set=rng.choice(["minimal", "extended"]),
                hyperparams=rng.choice(all_hp),
                cv_folds=folds,
                seed=seed,
            )
            for _ in range(max_configs)
        ]

    logger.info(f"Strategy: {strategy}, max_configs: {max_configs}, folds: {folds}")

    data = _synthetic_data()
    git_commit = _git_commit()

    results: list[BenchmarkResult] = []
    for cfg in configs:
        result = run_one(cfg, data)
        result.git_commit = git_commit
        result.notes = f"strategy={strategy}"
        results.append(result)
        logger.info(
            f"  {cfg.model_id:20}  rmsle={result.metrics['rmsle']:.4f}  "
            f"mae={result.metrics['mae']:.2f}  time={result.train_time_sec:.1f}s"
        )

    # Write report (delegated to report.py when called from compare)
    from transit_ai.benchmark.report import write_report
    write_report(results, output)
    logger.info(f"✅ Report written: {output}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strategy", choices=["grid", "random"], default="grid")
    p.add_argument("--max-configs", type=int, default=12)
    p.add_argument("--output", type=Path, default=Path(f"docs/reports/benchmark_{datetime.now(timezone.utc).date().isoformat()}.md"))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--folds", type=int, default=4)
    args = p.parse_args()
    return run_benchmark_sweep(
        strategy=args.strategy,
        max_configs=args.max_configs,
        output=args.output,
        seed=args.seed,
        folds=args.folds,
    )


if __name__ == "__main__":
    sys.exit(main())
