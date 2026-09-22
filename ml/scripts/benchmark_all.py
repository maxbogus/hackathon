#!/usr/bin/env python3
"""Full benchmark grid: BaselineMean + XGBoost + GRU + Hybrid (12 configs × 4 folds).

Usage:
    cd ml && uv run python scripts/benchmark_all.py
    make benchmark-all

⚠ Может занять 5-10 минут на RTX 5060 (GRU configs самые тяжёлые).
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ml/
sys.path.insert(0, str(ROOT))

from transit_ai.benchmark.cli import run_benchmark_sweep

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strategy", choices=["grid", "random"], default="grid")
    p.add_argument("--max-configs", type=int, default=12)
    p.add_argument("--folds", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    output = ROOT.parent / "docs" / "reports" / f"benchmark_{datetime.now(UTC).date().isoformat()}.md"
    sys.exit(run_benchmark_sweep(
        strategy=args.strategy,
        max_configs=args.max_configs,
        output=output,
        seed=args.seed,
        folds=args.folds,
    ))
