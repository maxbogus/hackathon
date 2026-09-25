#!/usr/bin/env python3
"""Train XGBoostRoutePredictor on hackathon real data (T-152).

Usage:
    uv run --directory ml python scripts/train_xgboost.py
        [--start-date 2025-01-01] [--end-date 2025-08-31]   # train period
        [--holdout-start 2025-09-01] [--holdout-end 2025-10-31]  # eval period
        [--model-id xgboost_v2]
        [--n-estimators 200] [--max-depth 6] [--learning-rate 0.1]
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
from transit_ai.models.xgboost_route import XGBoostRoutePredictor
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
    p.add_argument("--model-id", default="xgboost_v2")
    p.add_argument("--n-estimators", type=int, default=200)
    p.add_argument("--max-depth", type=int, default=6)
    p.add_argument("--learning-rate", type=float, default=0.1)
    args = p.parse_args()

    train_start = datetime.fromisoformat(args.start_date).replace(tzinfo=UTC)
    holdout_start = datetime.fromisoformat(args.holdout_start).replace(tzinfo=UTC)
    holdout_end = datetime.fromisoformat(args.holdout_end).replace(tzinfo=UTC)

    print("=" * 60)
    print(f"XGBoost train (T-152) — model: {args.model_id}")
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

    # 2. Train
    model = XGBoostRoutePredictor(
        model_id=args.model_id,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
    )
    print(f"Training {args.n_estimators} trees x 3 quantiles ...")
    model.fit(all_df)  # fit на полном ряду для корректных lag features
    print("Fit done.")

    # 3. Evaluate on holdout
    test_pred = model.predict_batch(holdout_df)
    metrics = compute_metrics(holdout_df["boardings"].values, test_pred)
    print()
    print(f"Holdout WAPE-score (сен–окт, XGBoost): {metrics['wape_score']:.4f}")
    print(
        f"  MAE={metrics['mae']:.1f}, WAPE={metrics['wape']:.4f}, "
        f"RMSLE={metrics['rmsle']:.4f}"
    )

    # 4. Save model + meta
    artifact_dir = ARTIFACTS_DIR / args.model_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.pkl"
    model.save(str(model_path))
    print(f"Saved model: {model_path}")

    meta = {
        "model_id": args.model_id,
        "kind": "xgboost_route",
        "trained_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit_short(),
        "seed": model.seed,
        "train_data_hash": "pending",  # TODO: sha256 от parquet
        "metrics": {
            "rmsle": metrics["rmsle"],
            "mae": metrics["mae"],
            "wape": metrics["wape"],
            "wape_score": metrics["wape_score"],
        },
        "hyperparams": {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "learning_rate": args.learning_rate,
        },
        "horizons": ["day"],
        "granularities": ["hour"],
    }
    meta_path = artifact_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"Saved meta: {meta_path}")

    # 5. SUBMISSION CANDIDATE (T-149 / clinerule 24)
    # Без реального submission CSV — только candidate для модели
    # Полноценный candidate появится после make_submission.py с этим model
    print()
    print("NOTE: run make submission SUBMISSION_ID=v5-xgboost to generate CSV")
    print(
        f"      Holdout WAPE={metrics['wape_score']:.4f} — это для сравнения с baseline"
    )

    return 0


if __name__ == "__main__":
    import pandas as pd

    sys.exit(main())
