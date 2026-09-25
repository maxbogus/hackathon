#!/usr/bin/env python3
"""CLI: print summary of hackathon real dataset (T-143).

Usage:
    uv run --directory ml python scripts/inspect_real.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABELS_DIR = REPO_ROOT / "data" / "real" / "labels"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--labels-dir",
        type=Path,
        default=DEFAULT_LABELS_DIR,
        help="Path to labels_day_*.csv files",
    )
    args = p.parse_args()

    if not (args.labels_dir / "labels_day_train.csv").exists():
        print(f"❌ Labels not found: {args.labels_dir}", file=sys.stderr)
        return 1

    src = RealSource(labels_dir=args.labels_dir)

    # Full dataset
    full = src.load_ridership(
        DateRange(datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 10, 31, tzinfo=UTC))
    )

    print("=" * 60)
    print("Hackathon Real Dataset Summary")
    print("=" * 60)
    print(f"Labels dir:  {args.labels_dir}")
    print(f"Total rows:  {len(full):,}")
    print(f"Date range:  {full['date'].min().date()} → {full['date'].max().date()}")
    print(f"Routes:      {sorted(full['route_id'].unique().tolist())}")
    print(f"Total boardings: {int(full['boardings'].sum()):,}")
    print(f"Mean boardings/hour: {full['boardings'].mean():.1f}")
    print(f"Median boardings/hour: {full['boardings'].median():.1f}")
    print(f"Max boardings/hour: {full['boardings'].max():.0f}")
    print(f"Hours with data: {sorted(full['hour'].unique().tolist())}")
    print()

    # Per-route breakdown
    print("Per-route stats:")
    print("-" * 60)
    by_route = full.groupby("route_id").agg(
        rows=("boardings", "size"),
        total=("boardings", "sum"),
        mean=("boardings", "mean"),
        max=("boardings", "max"),
    )
    print(by_route.to_string())
    print()

    # Per-hour breakdown
    print("Per-hour mean boardings (across all routes/dates):")
    print("-" * 60)
    by_hour = full.groupby("hour")["boardings"].mean().round(1)
    print(by_hour.to_string())
    print()

    # Validation check
    print("Per-month rows (sanity check):")
    print("-" * 60)
    full["month"] = full["date"].dt.to_period("M")
    by_month = full.groupby("month").size()
    print(by_month.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
