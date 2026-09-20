#!/usr/bin/env python3
"""run_benchmark.py — entry point for ML benchmark pipeline.

Делегирует в ml.transit_ai.benchmark.cli.

Usage:
    uv run python scripts/run_benchmark.py --strategy grid --max-configs 12 \\
        --output docs/reports/benchmark_<date>.md

Source: clinerule 19-ml-benchmark-pipeline.md.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--strategy", choices=["grid", "random"], default="grid")
    p.add_argument("--max-configs", type=int, default=12)
    p.add_argument("--output", type=Path, default=ROOT / "docs" / "reports" / f"benchmark_{date.today().isoformat()}.md")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--folds", type=int, default=4)
    args = p.parse_args()

    # Delegate to ml.transit_ai.benchmark.cli (when implemented in T-038)
    try:
        from transit_ai.benchmark.cli import run_benchmark_sweep
        return run_benchmark_sweep(
            strategy=args.strategy,
            max_configs=args.max_configs,
            output=args.output,
            seed=args.seed,
            folds=args.folds,
        )
    except ImportError as e:
        print(f"⚠ ml.transit_ai.benchmark не реализован (T-038 in progress): {e}")
        print("   Placeholder: создаю пустой report для smoke-test.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            f"# Benchmark Report ({date.today()})\n\n"
            f"⚠ Benchmark pipeline не реализован. См. clinerule 19.\n\n"
            f"Параметры:\n- strategy: {args.strategy}\n- max_configs: {args.max_configs}\n- folds: {args.folds}\n- seed: {args.seed}\n",
            encoding="utf-8",
        )
        print(f"📝 Wrote placeholder {args.output}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
