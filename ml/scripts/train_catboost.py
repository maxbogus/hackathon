#!/usr/bin/env python3
"""Train CatBoostRoutePredictor on hackathon real data (T-173).

Usage:
    uv run --directory ml python scripts/train_catboost.py
        [--start-date 2025-01-01] [--end-date 2025-08-31]   # train period
        [--holdout-start 2025-09-01] [--holdout-end 2025-10-31]  # eval period
        [--model-id catboost_v1]
        [--iterations 300] [--depth 6] [--learning-rate 0.05]
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
from transit_ai.models.catboost_route import CatBoostRoutePredictor
from transit_ai.reports.metrics import compute_metrics

SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
REPO_ROOT = ML_DIR.parent
DEFAULT_TRAIN_START = datetime(2025, 1, 1, tzinfo=UTC)
DEFAULT_TRAIN_END = datetime(2025, 8, 31, tzinfo=UTC)
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
        default="2025-08-31",
        help="Train END (data from start-date до end-date inclusive)",
    )
    p.add_argument("--holdout-start", default="2025-09-01")
    p.add_argument("--holdout-end", default="2025-10-31")
    p.add_argument("--model-id", default="catboost_v1")
    p.add_argument("--iterations", type=int, default=300)
    p.add_argument("--depth", type=int, default=6)
    p.add_argument("--learning-rate", type=float, default=0.05)
    args = p.parse_args()

    train_start = datetime.fromisoformat(args.start_date).replace(tzinfo=UTC)
    holdout_start = datetime.fromisoformat(args.holdout_start).replace(tzinfo=UTC)
    holdout_end = datetime.fromisoformat(args.holdout_end).replace(tzinfo=UTC)

    print("=" * 60)
    print(f"CatBoost train (T-173) — model: {args.model_id}")
    print("=" * 60)
    print(f"Train:    {args.start_date} → {args.end_date}")
    print(f"Holdout:  {args.holdout_start} → {args.holdout_end}")

    # 1. Load ВСЕ данные (train + holdout) для корректных lag features
    src = RealSource()
    all_df = src.load_ridership(DateRange(train_start, holdout_end))
    print(f"All rows (train+holdout): {len(all_df):,}")

    train_mask = all_df["timestamp"] < pd.Timestamp(holdout_start).tz_localize(None)
    train_df = all_df[train_mask].copy()
    holdout_df = all_df[~train_mask].copy()
    print(f"Train rows:    {len(train_df):,}")
    print(f"Holdout rows:  {len(holdout_df):,}")

    # 2. Train CatBoost
    print(
        f"Training {args.iterations} iterations x depth={args.depth} lr={args.learning_rate} ..."
    )
    model = CatBoostRoutePredictor(
        model_id=args.model_id,
        iterations=args.iterations,
        depth=args.depth,
        learning_rate=args.learning_rate,
    )
    model.fit(all_df)
    print("Fit done.")

    # 3. Evaluate on holdout
    holdout_pred = model.predict_batch(holdout_df)
    metrics = compute_metrics(holdout_df["boardings"].values, holdout_pred)
    print(
        f"Holdout WAPE-score (сен–окт, CatBoost): {metrics['wape_score']:.4f}  "
        f"(MAE={metrics['mae']:.1f}, WAPE={metrics['wape']:.4f}, "
        f"RMSLE={metrics['rmsle']:.4f})"
    )

    # 4. Save artifact (используем .save() чтобы совпадало с .load())
    out_dir = ARTIFACTS_DIR / args.model_id
    out_dir.mkdir(parents=True, exist_ok=True)
    model_pkl = out_dir / "model.pkl"
    model.save(str(model_pkl))
    print(f"Saved model: {model_pkl}")

    # 5. Write meta.json (по образцу XGBoost)
    meta = {
        "model_id": args.model_id,
        "kind": "catboost_route",
        "trained_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit_short(),
        "seed": 42,
        "train_data_hash": _resolve_train_data_hash(),
        "metrics": metrics,
        "hyperparams": {
            "iterations": args.iterations,
            "depth": args.depth,
            "learning_rate": args.learning_rate,
        },
        "horizons": ["day"],
        "granularities": ["hour"],
    }
    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"Saved meta: {meta_path}")

    print()
    print(f"Holdout WAPE-score = {metrics['wape_score']:.4f}")
    print("Run make submission or scripts/blend.py для генерации CSV")
    return 0


def _resolve_train_data_hash() -> str:
    """F-114: подтянуть sha256 train.csv из lineage snapshot."""
    snap_path = (
        Path(__file__).resolve().parents[2]
        / "docs" / "lineage" / "datasets" / "real_ridership.json"
    )
    if not snap_path.is_file():
        print(
            f"WARN: lineage snapshot не найден ({snap_path}); "
            "train_data_hash='pending'. Снять: make lineage-snapshot-real"
        )
        return "pending"
    try:
        from transit_ai.lineage.snapshot import read as _read_snapshot
        return _read_snapshot(snap_path).sha256
    except Exception as exc:
        print(f"WARN: snapshot read failed {snap_path}: {exc}")
        return "pending"


if __name__ == "__main__":
    import pandas as pd

    sys.exit(main())
