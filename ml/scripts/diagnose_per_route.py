#!/usr/bin/env python3
"""CLI: per-route / per-hour / per-weekday WAPE диагностика (T-146).

Использование:
    make diagnose
    uv run --directory ml python scripts/diagnose_per_route.py

Выводит:
- Overall WAPE-score на holdout (сен-окт 2025)
- Per-route WAPE-score (отсортировано ASC, слабые сверху)
- Per-hour WAPE-score
- Per-weekday WAPE-score
- Список маршрутов с WAPE < 0.85 (слабые места)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from transit_ai.calibration.route_bias import apply_route_bias, compute_route_bias
from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.route_baseline import RouteBaselineMean
from transit_ai.reports.diagnose import diagnose

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = REPO_ROOT / "ml"


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def _print_dict_sorted(d: dict, asc: bool = True, n: int | None = None) -> None:
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=not asc)
    if n is not None:
        items = items[:n]
    for k, v in items:
        print(f"  {k!s:>10} : {_fmt(v)}")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--train-start", default="2025-01-01")
    p.add_argument("--train-end", default="2025-08-31")
    p.add_argument("--test-start", default="2025-09-01")
    p.add_argument("--test-end", default="2025-10-31")
    p.add_argument(
        "--threshold", type=float, default=0.85, help="WAPE threshold for 'weak' routes"
    )
    args = p.parse_args()

    train_start = datetime.strptime(args.train_start, "%Y-%m-%d").replace(tzinfo=UTC)
    train_end = datetime.strptime(args.train_end, "%Y-%m-%d").replace(tzinfo=UTC)
    test_start = datetime.strptime(args.test_start, "%Y-%m-%d").replace(tzinfo=UTC)
    test_end = datetime.strptime(args.test_end, "%Y-%m-%d").replace(tzinfo=UTC)

    print("=" * 60)
    print("Per-route WAPE diagnose (T-146)")
    print("=" * 60)
    print(f"Train: {args.train_start} → {args.train_end}")
    print(f"Test:  {args.test_start} → {args.test_end}")
    print()

    # Train + predict
    src = RealSource()
    train = src.load_ridership(DateRange(train_start, train_end))
    test = src.load_ridership(DateRange(test_start, test_end))
    print(f"Train rows: {len(train):,}, Test rows: {len(test):,}")

    model = RouteBaselineMean()
    model.fit(train)
    preds = model.predict_batch(test)

    # Diagnose (без calibration)
    result = diagnose(test, preds)
    print()
    print(f"Overall WAPE-score (без calibration): {_fmt(result['overall'])}")
    print(
        f"N points: {result['n_points']:,}, Total boardings: {result['total_boardings']:,.0f}"
    )
    print()

    print("Per-route (sorted ASC, weak first):")
    print("-" * 40)
    _print_dict_sorted(result["per_route"], asc=True)
    weak_routes = [r for r, s in result["per_route"].items() if s < args.threshold]
    if weak_routes:
        print()
        print(f"⚠️  Weak routes (WAPE < {args.threshold}): {sorted(weak_routes)}")
    print()

    print("Per-hour (0..23):")
    print("-" * 40)
    _print_dict_sorted(result["per_hour"], asc=True)
    print()

    print("Per-weekday (0=Mon, 6=Sun):")
    print("-" * 40)
    _print_dict_sorted(result["per_weekday"], asc=True)

    # --- T-147: compare with bias correction ---
    print()
    print("=" * 60)
    print("After per-route bias correction (T-147, log-space median)")
    print("=" * 60)
    # Biases вычисляются на train (in-sample, оптимистично).
    train_pred_in_sample = model.predict_batch(train)
    biases = compute_route_bias(
        train_actual=train["boardings"],
        train_pred=pd.Series(train_pred_in_sample),
        route_ids=train["route_id"],
    )
    print("Per-route biases (log-space):")
    for r, b in sorted(biases.items()):
        ratio = np.exp(b)
        print(f"  route {r:>3}: bias={b:+.4f} → multiplier={ratio:.4f}")

    preds_calibrated = apply_route_bias(
        preds, test["route_id"].astype(int).values, biases
    )
    result_cal = diagnose(test, preds_calibrated)
    print()
    print(f"Overall WAPE-score (calibrated): {_fmt(result_cal['overall'])}")
    print(f"Δ = {result_cal['overall'] - result['overall']:+.4f}")
    print()
    print("Per-route (calibrated, sorted ASC, weak first):")
    print("-" * 40)
    for r, s in sorted(result_cal["per_route"].items(), key=lambda kv: kv[1]):
        before = result["per_route"].get(int(r), 0.0)
        print(f"  {r!s:>10} : {_fmt(s)} (Δ {s - before:+.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
