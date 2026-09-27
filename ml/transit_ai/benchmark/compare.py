"""Compare multiple benchmark reports → leaderboard.

Usage:
    uv run python -m transit_ai.benchmark.compare --reports docs/reports/benchmark_*.json
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from transit_ai.benchmark.configs import BenchmarkResult
from transit_ai.benchmark.report import write_report


def load_reports(patterns: list[str]) -> list[BenchmarkResult]:
    """Load BenchmarkResult list из N JSON files."""
    results: list[BenchmarkResult] = []
    for pattern in patterns:
        for path_str in glob.glob(pattern):
            path = Path(path_str)
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data.get("results", []):
                # Reconstruct BenchmarkResult
                from transit_ai.benchmark.configs import BenchmarkConfig

                cfg = BenchmarkConfig(**item["config"])
                item["config"] = cfg
                results.append(BenchmarkResult(**item))
    return results


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--reports", nargs="+", required=True, help="Glob patterns for JSON reports"
    )
    p.add_argument("--output", type=Path, default=Path("docs/reports/leaderboard.md"))
    args = p.parse_args()

    results = load_reports(args.reports)
    if not results:
        print("❌ No reports loaded. Check --reports paths.")
        return 1

    print(f" Loaded {len(results)} benchmark results")
    write_report(results, args.output)
    print(f"✅ Leaderboard written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
