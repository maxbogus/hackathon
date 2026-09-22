#!/usr/bin/env python3
"""CLI: generate predictions with active model → predictions/*.parquet (T-033).

Usage:
    make predict
    uv run --directory ml python scripts/predict.py [--horizon day] [--model-id baseline_v1]
        [--from 2026-02-01T00:00:00] [--to 2026-02-02T00:00:00]
        [--stop-ids 1,2,3] [--output-dir predictions] [--scenario-id baseline]

Defaults:
    horizon = day, granularity = hour
    from_dt = now, to_dt = now + horizon hours
    model_id = active.json if --model-id not given
    stop_ids = 1..10 (fallback) if --stop-ids not given
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from transit_ai.training.predict import PredictConfig, predict

logger = logging.getLogger("predict_cli")

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--horizon", choices=["day", "month", "year"], default="day")
    p.add_argument(
        "--granularity", choices=["hour", "day", "month"], default="hour"
    )
    p.add_argument("--model-id", default=None, help="Override active.json")
    p.add_argument(
        "--from",
        dest="from_dt",
        default=None,
        help="ISO datetime, e.g. 2026-02-01T00:00:00 (default: now)",
    )
    p.add_argument(
        "--to",
        dest="to_dt",
        default=None,
        help="ISO datetime (default: now + horizon hours)",
    )
    p.add_argument(
        "--stop-ids",
        default=None,
        help="Comma-separated list, e.g. 1,2,3 (default: 1..10)",
    )
    p.add_argument(
        "--scenario-id", default=None, help="Optional scenario label (Monte Carlo)"
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override default predictions/ output directory",
    )
    args = p.parse_args()

    stop_ids: list[int] = []
    if args.stop_ids:
        stop_ids = sorted({int(s) for s in args.stop_ids.split(",") if s.strip()})

    from_dt: datetime | None = None
    to_dt: datetime | None = None
    if args.from_dt:
        from_dt = datetime.fromisoformat(args.from_dt)
    if args.to_dt:
        to_dt = datetime.fromisoformat(args.to_dt)
    if (from_dt is None) != (to_dt is None):
        print("❌ Both --from and --to must be set or both omitted.", file=sys.stderr)
        return 2

    cfg = PredictConfig(
        model_id=args.model_id,
        from_dt=from_dt,
        to_dt=to_dt,
        horizon=args.horizon,
        granularity=args.granularity,
        stop_ids=stop_ids,
        scenario_id=args.scenario_id,
        output_dir=args.output_dir if args.output_dir else PredictConfig().output_dir,
    )

    print(
        f"🔮 Predicting: model_id={cfg.model_id or '(active)'!r}, "
        f"horizon={cfg.horizon}, granularity={cfg.granularity}, "
        f"stop_ids={stop_ids or '[1..10]'}, "
        f"window={from_dt or 'now'} → {to_dt or 'now + horizon'}"
    )

    try:
        out_path = predict(cfg)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"❌ Prediction failed: {e}", file=sys.stderr)
        return 1

    print(f"\n✅ Done. Output: {out_path}")
    print("   Next: open in pandas/polars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
