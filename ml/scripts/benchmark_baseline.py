#!/usr/bin/env python3
"""Smoke benchmark BaselineMean on synthetic data (~30 sec).

Usage:
    cd ml && uv run python scripts/benchmark_baseline.py
    make benchmark-baseline
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ml/
sys.path.insert(0, str(ROOT))

from transit_ai.benchmark.cli import run_benchmark_sweep


if __name__ == "__main__":
    output = ROOT.parent / "docs" / "reports" / "benchmark_baseline_smoke.md"
    sys.exit(run_benchmark_sweep(
        strategy="grid",
        max_configs=1,  # только BaselineMean
        output=output,
        seed=42,
        folds=2,  # быстрый smoke (2 folds)
    ))
