#!/usr/bin/env python3
"""CLI: fit per-bucket calibration on holdout → ml/artifacts/<model>/calibration.json (T-034).

Usage:
    make calibrate
    uv run --directory ml python scripts/calibrate.py [--holdout /path/holdout.parquet] [--prior 100]

Pipeline:
1. Load holdout parquet (y_true, y_pred, stop_id, timestamp)
2. Compute per-bucket biases (stop_id, weekday, hour) with shrinkage
3. Save calibration.json в ml/artifacts/<active>/
4. predict.py автоматически применяет calibration если файл существует (T-033)

References:
- ~/Repositories/contest/ecup26-user-value/scripts/apply_bucket_calibration.py
- docs/schemas/prediction_artifact.schema.json (calibration field)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from transit_ai.training.calibrate import CalibrateConfig, fit_calibration
from transit_ai.training.registry import ModelRegistry

logger = logging.getLogger("calibrate_cli")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_holdout_path(artifacts_dir: Path) -> Path:
    """Try to find a holdout parquet in the conventional location."""
    candidates = [
        REPO_ROOT / "data" / "validation_reports" / "holdout.parquet",
        REPO_ROOT / "predictions" / "holdout.parquet",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return candidates[0]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--holdout",
        type=Path,
        default=None,
        help="Path to holdout parquet (default: data/validation_reports/holdout.parquet)",
    )
    p.add_argument(
        "--prior", type=float, default=100.0, help="Shrinkage prior (default: 100)"
    )
    p.add_argument(
        "--min-obs",
        type=int,
        default=5,
        help="Min observations per bucket (default: 5, ниже → bucket пропускается)",
    )
    p.add_argument("--model-id", default=None, help="Override active.json")
    p.add_argument(
        "--strategy",
        choices=["bucket", "shrink", "segmental"],
        default="bucket",
        help="Calibration strategy (default: bucket)",
    )
    args = p.parse_args()

    artifacts_dir = ModelRegistry.DEFAULT_ARTIFACTS_DIR

    holdout_path = args.holdout or _default_holdout_path(artifacts_dir)
    if not holdout_path.is_file():
        print(f"❌ Holdout parquet not found: {holdout_path}", file=sys.stderr)
        print(
            "   Generate via: uv run --directory ml python scripts/evaluate.py --reports-dir <dir>",
            file=sys.stderr,
        )
        return 2

    cfg = CalibrateConfig(
        artifacts_dir=artifacts_dir,
        model_id=args.model_id,
        holdout_parquet=holdout_path,
        prior=args.prior,
        min_obs_per_bucket=args.min_obs,
    )

    print(
        f" Fitting calibration: strategy={args.strategy}, prior={args.prior}, "
        f"min_obs={args.min_obs}"
    )
    print(f"   holdout = {holdout_path}")

    try:
        calib = fit_calibration(cfg)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Calibration failed: {e}", file=sys.stderr)
        return 1

    if calib is None:
        print("❌ No calibration produced", file=sys.stderr)
        return 1

    print()
    print(f"  buckets = {len(calib.biases_per_bucket)}")
    print(f"  n_obs = {calib.n_obs}")
    print(f"  global_bias = {calib.global_bias:.4f}")
    print("\n✅ Done. Next: make predict (will auto-apply calibration)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
