#!/usr/bin/env python3
"""Train GRURoutePredictor on hackathon real data (T-029, T-175).

Usage:
    uv run --directory ml python scripts/train_gru.py
        [--start-date 2025-01-01] [--end-date 2025-10-31]
        [--model-id gru_v1]
        [--seq-len 168] [--hidden 64] [--epochs 10]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.gru_route import GRURoutePredictor
from transit_ai.reports.metrics import compute_metrics

SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
REPO_ROOT = ML_DIR.parent
DEFAULT_TRAIN_START = datetime(2025, 1, 1, tzinfo=UTC)
DEFAULT_HOLDOUT_START = datetime(2025, 9, 1, tzinfo=UTC)
DEFAULT_HOLDOUT_END = datetime(2025, 10, 31, tzinfo=UTC)
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"


def git_commit_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--start-date", default="2025-01-01")
    p.add_argument(
        "--end-date",
        default="2025-10-31",
        help="End of full data (train+holdout)",
    )
    p.add_argument("--model-id", default="gru_v1")
    p.add_argument("--seq-len", type=int, default=168)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--epochs", type=int, default=10)
    args = p.parse_args()

    train_start = datetime.fromisoformat(args.start_date).replace(tzinfo=UTC)
    end_dt = datetime.fromisoformat(args.end_date).replace(tzinfo=UTC)

    print("=" * 60)
    print(f"GRU train (T-175) -- model: {args.model_id}")
    print("=" * 60)
    print(f"Train:    {args.start_date} -> {args.end_date}")
    print(f"seq_len:  {args.seq_len}, hidden: {args.hidden}, epochs: {args.epochs}")

    src = RealSource()
    df = src.load_ridership(DateRange(train_start, end_dt))
    print(f"Total rows: {len(df):,}")

    # Train + holdout split
    import pandas as pd

    holdout_mask = df["timestamp"] >= pd.Timestamp(DEFAULT_HOLDOUT_START).tz_localize(
        None
    )
    train_df = df[~holdout_mask].copy()
    holdout_df = df[holdout_mask].copy()
    print(f"Train:    {len(train_df):,} rows")
    print(f"Holdout:  {len(holdout_df):,} rows")

    model = GRURoutePredictor(
        model_id=args.model_id,
        seq_len=args.seq_len,
        hidden=args.hidden,
        epochs=args.epochs,
    )
    # Train on train+holdout (как XGBoost - для lag sequences)
    print(f"\nTraining {args.epochs} epochs x hidden={args.hidden}...")
    model.fit(df)

    # Evaluate on holdout
    print("\nEvaluating on holdout...")
    # Holdout predict with train as history
    preds = model.predict_batch(holdout_df, history=train_df)
    metrics = compute_metrics(holdout_df["boardings"].values, preds)
    print(
        f"Holdout WAPE-score (сен-окт, GRU): {metrics['wape_score']:.4f}  "
        f"(MAE={metrics['mae']:.1f}, WAPE={metrics['wape']:.4f}, "
        f"RMSLE={metrics['rmsle']:.4f})"
    )

    # Save artifact
    out_dir = ARTIFACTS_DIR / args.model_id
    out_dir.mkdir(parents=True, exist_ok=True)
    model_pkl = out_dir / "model.pkl"
    model.save(str(model_pkl))
    print(f"Saved model: {model_pkl}")

    # Meta
    meta = {
        "model_id": args.model_id,
        "kind": "gru_route",
        "trained_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit_short(),
        "seed": 42,
        "train_data_hash": "pending",
        "metrics": metrics,
        "hyperparams": {
            "seq_len": args.seq_len,
            "hidden": args.hidden,
            "epochs": args.epochs,
            "layers": 2,
        },
        "horizons": ["day"],
        "granularities": ["hour"],
    }
    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"Saved meta: {meta_path}")

    print(f"\nHoldout WAPE-score = {metrics['wape_score']:.4f}")
    print("Run scripts/blend.py --models gru_v1 xgboost_v9_events для ensemble")
    return 0


if __name__ == "__main__":
    sys.exit(main())
