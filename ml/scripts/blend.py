#!/usr/bin/env python3
"""Rank-average blend of N model artifacts (T-173).

Подход из evehicle_pred/scripts/blend.py: rankdata → mean → rescale к min/max.

Usage:
    uv run --directory ml python scripts/blend.py
        --models xgboost_v9_events catboost_v1
        --submission-id v10-blend
"""
from __future__ import annotations

import argparse
import pickle
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from transit_ai.blend.rank_average import weighted_mean_blend
from transit_ai.calibration.route_bias import apply_route_bias, compute_route_bias
from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.xgboost_route import build_lag_lookup
from transit_ai.reports.metrics import compute_metrics
from transit_ai.submission.candidate import print_candidate
from transit_ai.submission.manifest import write_manifest

# F-045: route 5 НЕ исключён — ground_truth содержит 1464 строки
ROUTES: tuple[int, ...] = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)
DEFAULT_TRAIN_START = datetime(2025, 1, 1, tzinfo=UTC)
DEFAULT_TRAIN_END = datetime(2025, 8, 31, tzinfo=UTC)
DEFAULT_HOLDOUT_START = datetime(2025, 9, 1, tzinfo=UTC)
DEFAULT_HOLDOUT_END = datetime(2025, 10, 31, tzinfo=UTC)
SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
REPO_ROOT = ML_DIR.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
DEFAULT_OUTPUT_DIR = (REPO_ROOT / "predictions").resolve()


def git_commit_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _load_model(model_id: str) -> object:
    pkl_path = ARTIFACTS_DIR / model_id / "model.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {pkl_path}")
    # XGBoostRoutePredictor имеет кастомный .load() класс-метод,
    # который читает boosters из отдельной директории.
    # CatBoostRoutePredictor — обычный pickle (dataclass).
    if model_id.startswith("xgboost"):
        from transit_ai.models.xgboost_route import XGBoostRoutePredictor
        return XGBoostRoutePredictor.load(str(pkl_path))
    if model_id.startswith("catboost"):
        from transit_ai.models.catboost_route import CatBoostRoutePredictor
        return CatBoostRoutePredictor.load(str(pkl_path))
    # Fallback — pickle
    with pkl_path.open("rb") as f:
        return pickle.load(f)


def build_full_grid(start_date, end_date, routes=ROUTES):
    days = (end_date.date() - start_date.date()).days + 1
    n_rows = days * len(routes) * 24
    rows = []
    for d_offset in range(days):
        d = (start_date + timedelta(days=d_offset)).date()
        for r in routes:
            for h in range(24):
                rows.append({"route": r, "date": d, "hour": h})
    return pd.DataFrame(rows), n_rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", required=True)
    p.add_argument("--start-date", default="2025-11-01")
    p.add_argument("--end-date", default="2025-12-31")
    p.add_argument("--submission-id", default=None)
    args = p.parse_args()

    n_models = len(args.models)
    print("=" * 60)
    print(f"Weighted-mean blend (T-173) - {n_models} models: {args.models}")
    print("=" * 60)

    src = RealSource()
    all_df = src.load_ridership(DateRange(DEFAULT_TRAIN_START, DEFAULT_HOLDOUT_END))
    train_mask = all_df["timestamp"] < pd.Timestamp(DEFAULT_HOLDOUT_START).tz_localize(None)
    train_df = all_df[train_mask].copy()
    holdout_df = all_df[~train_mask].copy()

    lag_lookup = build_lag_lookup(train_df)
    print(f"Built lag_lookup: {len(lag_lookup):,} entries")

    # Holdout: predict каждым, оценить WAPE-score, рассчитать веса
    holdout_preds_per_model = []
    holdout_wapes: list[float] = []
    for mid in args.models:
        model = _load_model(mid)
        preds = model.predict_batch(holdout_df, lag_lookup=lag_lookup)
        holdout_preds_per_model.append(preds)
        m = compute_metrics(holdout_df["boardings"].values, preds)
        holdout_wapes.append(m["wape"])
        print(f"  {mid:>25} -> WAPE-score={m['wape_score']:.4f}  (WAPE={m['wape']:.4f})")

    # Веса пропорциональны (1 - WAPE), нормализованы.
    # Лучшая модель (низкий WAPE) получает больший вес.
    inv_wape = [1.0 / max(w, 0.001) for w in holdout_wapes]
    sum_inv = sum(inv_wape)
    weights = [w / sum_inv for w in inv_wape]
    print(f"Weights (1/WAPE): {[f'{w:.3f}' for w in weights]}")

    blend_holdout = weighted_mean_blend(holdout_preds_per_model, weights=weights)
    metrics_blend = compute_metrics(holdout_df["boardings"].values, blend_holdout)
    print(f"Holdout WAPE-score (weighted blend): {metrics_blend['wape_score']:.4f}")

    # Per-route bias calibration (T-147)
    train_preds_per_model = [m.predict_batch(train_df, lag_lookup=lag_lookup)
                             for m in [_load_model(mid) for mid in args.models]]
    train_preds_blend = weighted_mean_blend(train_preds_per_model, weights=weights)
    route_biases = compute_route_bias(
        train_actual=train_df["boardings"],
        train_pred=pd.Series(train_preds_blend),
        route_ids=train_df["route_id"],
    )
    blend_holdout_calibrated = apply_route_bias(
        blend_holdout, holdout_df["route_id"].astype(int).values, route_biases
    )
    metrics_calibrated = compute_metrics(holdout_df["boardings"].values, blend_holdout_calibrated)
    print(f"Holdout WAPE-score (calibrated): {metrics_calibrated['wape_score']:.4f}  (delta {metrics_calibrated['wape_score'] - metrics_blend['wape_score']:+.4f})")

    # Submission grid
    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=UTC)
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=UTC)
    grid, expected_rows = build_full_grid(start_dt, end_dt)
    print(f"Submission grid: {grid.shape} (expected {expected_rows} rows)")

    pred_df = grid.rename(columns={"route": "route_id"})
    pred_df["date"] = pd.to_datetime(pred_df["date"])

    submission_preds = []
    for mid in args.models:
        model = _load_model(mid)
        preds = model.predict_batch(pred_df, lag_lookup=lag_lookup)
        submission_preds.append(preds)
    blend_submission = weighted_mean_blend(submission_preds, weights=weights)
    blend_submission = apply_route_bias(blend_submission, grid["route"].astype(int).values, route_biases)
    blend_submission = np.maximum(blend_submission, 0.0)
    grid["prediction"] = np.round(blend_submission, 2)

    # Save
    start_date_str = start_dt.strftime("%Y%m%d")
    end_date_str = end_dt.strftime("%Y%m%d")
    run_ts_str = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    blend_id = "_".join(args.models)
    csv_filename = f"submission_blend_{blend_id}_{start_date_str}_{end_date_str}_{run_ts_str}.csv"
    output = DEFAULT_OUTPUT_DIR / csv_filename
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(output, sep=";", index=False)
    print(f"Saved to: {output}")
    print(f"Total rows: {len(grid)} (expected {expected_rows})")
    print(f"Total predictions: {grid['prediction'].sum():,.0f} boardings")

    submission_id = args.submission_id or f"blend_{blend_id}"
    manifest_path = write_manifest(
        out_dir=output.parent,
        csv_filename=output.name,
        model_id=submission_id,
        model_uri=f"ml/artifacts/blend/{'+'.join(args.models)}",
        train_range=(DEFAULT_TRAIN_START.strftime("%Y-%m-%d"), DEFAULT_TRAIN_END.strftime("%Y-%m-%d")),
        sub_range=(args.start_date, args.end_date),
        row_count=len(grid),
        expected_rows=expected_rows,
        total_predictions=float(grid["prediction"].sum()),
        coefficients={"weather": 1.0, "event": 1.0, "season": 1.0},
        post_processing=["clip_negatives", "per_route_log_bias_calibration", "weighted_mean_blend"],
        holdout_wape_score=metrics_calibrated["wape_score"],
        submission_id=submission_id,
    )
    print(f"Manifest: {manifest_path} (submission_id={submission_id})")

    alias = output.parent / "submission.csv"
    alias.write_text(output.read_text())
    print(f"Alias: {alias} (convenience, NOT source-of-truth)")

    print_candidate(
        csv_path=output, manifest_path=manifest_path, model_id=submission_id,
        submission_id=submission_id, holdout_wape=metrics_calibrated["wape_score"],
        submission_start=args.start_date, submission_end=args.end_date,
        row_count=len(grid), total_predictions=float(grid["prediction"].sum()),
        expected_rows=expected_rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
