#!/usr/bin/env python3
"""Generate submission.csv для платформы хакатона (T-145).

Usage:
    make submission
    uv run --directory ml python scripts/make_submission.py
        [--start-date 2025-11-01] [--end-date 2025-12-31]
        [--model-id route_baseline_v1]
        [--coef-weather 1.0] [--coef-event 1.0] [--coef-season 1.0]
        [--output predictions/submission.csv]

Output:
    predictions/submission_<model_id>_<YYYYMMDD_HHMM>.csv
    Columns: route;date;hour;prediction (separator=';')
    Shape: 10 routes × 61 days × 24 hours = 14 640 строк (F-045: ground_truth покрывает все 10)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from transit_ai.calibration.route_bias import apply_route_bias, compute_route_bias
from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.route_baseline import RouteBaselineMean
from transit_ai.models.xgboost_route import XGBoostRoutePredictor, build_lag_lookup
from transit_ai.reports.metrics import compute_metrics
from transit_ai.submission.candidate import print_candidate
from transit_ai.submission.manifest import write_manifest

# F-045 (Q-A retract): route 5 НЕ исключён — ground_truth содержит 1464 строки.
# Submission покрывает все 10 маршрутов: 1, 5, 7, 11, 12, 17, 25, 26, 28, 50.
ROUTES: tuple[int, ...] = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)
DEFAULT_TRAIN_START = datetime(2025, 1, 1, tzinfo=UTC)
DEFAULT_TRAIN_END = datetime(2025, 8, 31, tzinfo=UTC)
DEFAULT_TEST_START = datetime(2025, 9, 1, tzinfo=UTC)
DEFAULT_TEST_END = datetime(2025, 10, 31, tzinfo=UTC)
DEFAULT_HOLDOUT_END = DEFAULT_TEST_END  # T-152 alias
DEFAULT_HOLDOUT_START = DEFAULT_TEST_START  # T-152 alias
SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
REPO_ROOT = ML_DIR.parent
DEFAULT_OUTPUT_DIR = (REPO_ROOT / "predictions").resolve()


def build_full_grid(
    start_date: datetime,
    end_date: datetime,
    routes: tuple[int, ...] = ROUTES,
) -> pd.DataFrame:
    """Build full grid: routes × dates × hours = full coverage."""
    days = (end_date.date() - start_date.date()).days + 1
    n_rows = days * len(routes) * 24
    rows = []
    for d_offset in range(days):
        cur = start_date + timedelta(days=d_offset)
        for route in routes:
            for hour in range(24):
                rows.append(
                    {
                        "route": route,
                        "date": cur.strftime("%Y-%m-%d"),
                        "hour": hour,
                    }
                )
    return pd.DataFrame(rows, columns=["route", "date", "hour"]), n_rows


def apply_coefs(value: float, weather: float, event: float, season: float) -> float:
    """Apply корректирующие коэффициенты (T-147)."""
    return value * weather * event * season


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--start-date",
        default="2025-11-01",
        help="First date for submission (default 2025-11-01)",
    )
    p.add_argument(
        "--end-date",
        default="2025-12-31",
        help="Last date for submission (default 2025-12-31)",
    )
    p.add_argument("--model-id", default="route_baseline_v1", help="Model id")
    p.add_argument(
        "--flags-file",
        default=None,
        help="Path to YAML flags file (T-174). Default: defaults.yaml из ml/transit_ai/config/.",
    )
    p.add_argument(
        "--model-kind",
        choices=["route_baseline", "xgboost_route"],
        default="route_baseline",
        help="Model kind (T-152: xgboost_route для XGBoost)",
    )
    p.add_argument(
        "--coef-weather",
        type=float,
        default=1.0,
        help="Weather correction coef (T-147)",
    )
    p.add_argument(
        "--coef-event", type=float, default=1.0, help="Event correction coef (T-147)"
    )
    p.add_argument(
        "--coef-season", type=float, default=1.0, help="Season correction coef (T-147)"
    )
    p.add_argument(
        "--submission-id",
        default=None,
        help="Human-readable submission id (R5 clinerule 23, default=model_id).",
    )
    p.add_argument("--output", default=None, help="Output CSV path")
    p.add_argument(
        "--use-recursive",
        action="store_true",
        help="T-153: use predict_recursive (rolling-window) вместо predict_batch+lag_lookup",
    )
    p.add_argument(
        "--recompute-days",
        type=int,
        default=7,
        help="T-153: размер окна для recursive forecast (default 7)",
    )
    p.add_argument(
        "--no-bias-calibration",
        action="store_true",
        help="T-178: skip per-route bias calibration (raw predictions only)",
    )
    p.add_argument(
        "--zero-hours",
        type=int,
        nargs="+",
        default=None,
        help="T-179: zero predictions for these hours (e.g. --zero-hours 0 1 2 3 4 5)",
    )
    p.add_argument(
        "--zero-weekends",
        action="store_true",
        help="T-180: zero predictions on Sat/Sun",
    )
    p.add_argument(
        "--zero-holidays",
        action="store_true",
        help="T-180: zero predictions on public holidays (2025-11..12)",
    )
    p.add_argument(
        "--zero-route",
        type=int,
        action="append",
        default=None,
        help="F-051/T-180: zero predictions for specific route(s). Repeatable: --zero-route 5",
    )
    p.add_argument(
        "--pred-cap",
        type=int,
        default=None,
        help="F-056..F-060: zero predictions where pred <= N (in target hours). E.g. --pred-cap 55 --cap-hours 0 1 2 3 4",
    )
    p.add_argument(
        "--cap-hours",
        type=int,
        nargs="+",
        default=None,
        help="F-060: hours where --pred-cap applies. Default: 0 1 2 3 4 (h0-4). Used with --pred-cap.",
    )
    args = p.parse_args()

    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=UTC)
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=UTC)

    print("=" * 60)
    print(f"Submission pipeline (T-145) — model: {args.model_id}")
    print("=" * 60)
    print(f"Date range: {args.start_date} → {args.end_date}")

    # 1. Load real data + train
    src = RealSource()
    # XGBoost использует полный ряд (train+holdout) для lag features
    if args.model_kind == "xgboost_route":
        all_df = src.load_ridership(DateRange(DEFAULT_TRAIN_START, DEFAULT_HOLDOUT_END))
        train_df = all_df[
            all_df["timestamp"] < pd.Timestamp(DEFAULT_HOLDOUT_START).tz_localize(None)
        ].copy()
        print(
            f"Train rows: {len(train_df):,} ({DEFAULT_TRAIN_START.date()} → {DEFAULT_TRAIN_END.date()})"
        )
        # T-174: load feature flags from --flags-file (or use defaults.yaml)
        if args.flags_file:
            from transit_ai.config.flags import FlagsRegistry

            registry = FlagsRegistry.from_yaml(Path(args.flags_file))
        else:
            from transit_ai.config.flags import FlagsRegistry

            registry = FlagsRegistry.default()
        feature_flags = registry.features
        print(
            f"Feature flags: use_poi={feature_flags.use_poi_features}, "
            f"use_events={feature_flags.use_events}, use_traffic={feature_flags.use_traffic}, "
            f"use_geo={feature_flags.use_geo_features}"
        )

        # Train XGBoost на полном ряду
        model = XGBoostRoutePredictor(model_id=args.model_id)
        model.fit(all_df, flags=feature_flags)
        print(
            f"Fit done: {model.n_estimators} trees x 3 quantiles "
            f"(features: {len(model.feature_names_)})"
        )
    else:
        train_df = src.load_ridership(DateRange(DEFAULT_TRAIN_START, DEFAULT_TRAIN_END))
        print(
            f"Train rows: {len(train_df):,} ({DEFAULT_TRAIN_START.date()} → {DEFAULT_TRAIN_END.date()})"
        )
        model = RouteBaselineMean(model_id=args.model_id)
        model.fit(train_df)
        print(f"Fit done: {len(model.table_)} (route, weekday, hour) buckets")

    # 2. Evaluate on test (holdout: sep-oct) — first WITHOUT calibration
    test_df = src.load_ridership(DateRange(DEFAULT_TEST_START, DEFAULT_TEST_END))
    test_pred = model.predict_batch(test_df)
    metrics_before = compute_metrics(test_df["boardings"].values, test_pred)
    print()
    print(
        f"Holdout WAPE-score (сен–окт, без calibration): {metrics_before['wape_score']:.4f}"
    )
    print(
        f"  MAE={metrics_before['mae']:.1f}, WAPE={metrics_before['wape']:.4f}, "
        f"RMSLE={metrics_before['rmsle']:.4f}"
    )

    # 2b. Compute per-route bias on TRAIN (in-sample) → apply to test (T-147)
    # T-178: --no-bias-calibration skips this step (raw predictions only)
    # In-sample bias — оптимистичная оценка (модель видела эти данные),
    # но показывает верхнюю границу эффекта calibration.
    if args.no_bias_calibration:
        print("T-178: SKIP per-route bias calibration (raw predictions)")
        route_biases = {}
        test_pred_calibrated = test_pred
        metrics_after = metrics_before
    else:
        train_pred_in_sample = model.predict_batch(train_df)
        route_biases = compute_route_bias(
            train_actual=train_df["boardings"],
            train_pred=pd.Series(train_pred_in_sample),
            route_ids=train_df["route_id"],
        )
        print(f"Per-route biases (log-space): {route_biases}")
        test_pred_calibrated = apply_route_bias(
            test_pred, test_df["route_id"].astype(int).values, route_biases
        )
        metrics_after = compute_metrics(test_df["boardings"].values, test_pred_calibrated)
    print(
        f"Holdout WAPE-score (сен–окт, calibrated): {metrics_after['wape_score']:.4f} "
        f"(Δ {metrics_after['wape_score'] - metrics_before['wape_score']:+.4f})"
    )

    # 3. Build full grid for submission
    grid, expected_rows = build_full_grid(start_dt, end_dt)
    print(f"Submission grid: {grid.shape} (expected {expected_rows} rows)")

    # 4. Predict each grid row
    # predict_batch expects route_id/date/hour cols (matching RealSource output)
    pred_df = grid.rename(columns={"route": "route_id"})
    pred_df["date"] = pd.to_datetime(pred_df["date"])

    # T-152-fallback: для XGBoost при inference (submission period) lag/rolling
    # фичей считаем через build_lag_lookup (mean из train по (route, weekday, hour)).
    # T-153: --use-recursive использует predict_recursive (rolling-window forecast).
    lag_lookup = None
    if args.model_kind == "xgboost_route":
        lag_lookup = build_lag_lookup(train_df)
        print(
            f"Built lag_lookup: {len(lag_lookup):,} entries (route, weekday, hour) -> mean"
        )
        if args.use_recursive:
            print(
                f"T-153: predict_recursive (window={args.recompute_days}d) "
                f"→ {len(pred_df):,} predictions"
            )
            preds = model.predict_recursive(
                history=train_df,
                future_grid=pred_df,
                recompute_every_days=args.recompute_days,
            )
        else:
            preds = model.predict_batch(pred_df, lag_lookup=lag_lookup)
    else:
        preds = model.predict_batch(pred_df)

    # Apply per-route bias correction (T-147)
    # T-178: skip if --no-bias-calibration
    if not args.no_bias_calibration:
        preds = apply_route_bias(preds, grid["route"].astype(int).values, route_biases)

    # T-179: zero specific hours (e.g. --zero-hours 0 1 2 3 4 5)
    if args.zero_hours:
        hours_mask = grid["hour"].isin(args.zero_hours)
        n_zeroed = hours_mask.sum()
        if n_zeroed > 0:
            preds[hours_mask] = 0.0
            print(f"T-179: zeroed {n_zeroed:,} rows for hours={args.zero_hours}")

    # F-051/T-180: zero specific route(s) (e.g. --zero-route 5 for missing-data route)
    if args.zero_route:
        for rid in args.zero_route:
            route_mask = grid["route"].astype(int) == rid
            n_route = route_mask.sum()
            if n_route > 0:
                preds[route_mask] = 0.0
                print(f"F-051: zeroed {n_route:,} rows for route_id={rid}")

    # F-056..F-060: cap predictions in specific hours (pred <= N → 0)
    if args.pred_cap is not None:
        cap_hours = args.cap_hours if args.cap_hours else [0, 1, 2, 3, 4]
        cap_mask = grid["hour"].isin(cap_hours) & (preds <= args.pred_cap)
        n_cap = cap_mask.sum()
        if n_cap > 0:
            preds[cap_mask] = 0.0
            print(f"F-060: zeroed {n_cap:,} rows where pred<={args.pred_cap} in hours={cap_hours}")

    # T-180: zero weekends (Sat=5, Sun=6) and/or holidays
    grid_dates = pd.to_datetime(grid["date"])
    weekday = grid_dates.dt.weekday  # 0=Mon, 6=Sun
    if args.zero_weekends:
        weekend_mask = weekday.isin([5, 6])
        n_wknd = weekend_mask.sum()
        if n_wknd > 0:
            preds[weekend_mask] = 0.0
            print(f"T-180: zeroed {n_wknd:,} weekend rows (Sat+Sun)")
    if args.zero_holidays:
        # Public holidays in Russia, Nov-Dec 2025 (4 ноября — День народного единства)
        HOLIDAYS_2025_11_12 = {"2025-11-04"}  # День народного единства
        holiday_mask = grid_dates.dt.strftime("%Y-%m-%d").isin(HOLIDAYS_2025_11_12)
        n_hol = holiday_mask.sum()
        if n_hol > 0:
            preds[holiday_mask] = 0.0
            print(f"T-180: zeroed {n_hol:,} holiday rows ({sorted(HOLIDAYS_2025_11_12)})")

    # Apply coefficients
    coef_product = args.coef_weather * args.coef_event * args.coef_season
    if coef_product != 1.0:
        preds = preds * coef_product
        print(
            f"Applied coefficients: weather={args.coef_weather}, event={args.coef_event}, "
            f"season={args.coef_season} → total x{coef_product}"
        )

    # Clip negatives (defensive)
    preds = np.maximum(preds, 0.0)

    # F-045: predictions float (2 знака) — платформа принимает float или округляет сама.
    # Q-A Q18 про integer был ошибочным (F-045 retract F-042).
    grid["prediction"] = np.round(preds, 2)

    # 5. Save — R1 clinerule 23: submission_<model>_<start_date>_<end_date>_<run_ts>.csv
    start_date_str = start_dt.strftime("%Y%m%d")
    end_date_str = end_dt.strftime("%Y%m%d")
    run_ts_str = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    if args.output:
        output = Path(args.output)
        # F-035: если путь относительный, resolveировать относительно REPO_ROOT,
        # иначе cwd=ml/ даст ml/predictions/ вместо predictions/
        if not output.is_absolute():
            output = (REPO_ROOT / output).resolve()
    else:
        csv_filename = f"submission_{args.model_id}_{start_date_str}_{end_date_str}_{run_ts_str}.csv"
        output = DEFAULT_OUTPUT_DIR / csv_filename
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(output, sep=";", index=False)
    print(f"Saved to: {output}")
    print(f"Total rows: {len(grid)} (expected {expected_rows})")
    print(f"Total predictions: {grid['prediction'].sum():,.0f} boardings")

    # 6. Write manifest.json рядом с CSV (R2 clinerule 23, T-148a)
    submission_id = args.submission_id or args.model_id
    coef_product = args.coef_weather * args.coef_event * args.coef_season
    applied_coefs = {
        "weather": args.coef_weather,
        "event": args.coef_event,
        "season": args.coef_season,
    }
    post_processing = ["clip_negatives"]
    if coef_product != 1.0:
        post_processing.append("coef_multiplier")
    if route_biases and not args.no_bias_calibration:
        post_processing.append("per_route_log_bias_calibration")
    if args.no_bias_calibration:
        post_processing.append("no_bias_calibration_T-178")
    if args.zero_hours:
        post_processing.append(f"zero_hours_{args.zero_hours}_T-179")
    if args.zero_weekends:
        post_processing.append("zero_weekends_T-180")
    if args.zero_holidays:
        post_processing.append("zero_holidays_T-180")
    if args.zero_route:
        post_processing.append(f"zero_route_{args.zero_route}_F-051")
    if args.pred_cap is not None:
        cap_hours = args.cap_hours if args.cap_hours else [0, 1, 2, 3, 4]
        post_processing.append(f"pred_cap_{args.pred_cap}_hours_{cap_hours}_F-060")

    model_uri = f"ml/artifacts/{args.model_id}/model.pkl"
    manifest_path = write_manifest(
        out_dir=output.parent,
        csv_filename=output.name,
        model_id=args.model_id,
        model_uri=model_uri,
        train_range=(
            DEFAULT_TRAIN_START.strftime("%Y-%m-%d"),
            DEFAULT_TRAIN_END.strftime("%Y-%m-%d"),
        ),
        sub_range=(args.start_date, args.end_date),
        row_count=len(grid),
        expected_rows=expected_rows,
        total_predictions=float(grid["prediction"].sum()),
        coefficients=applied_coefs,
        post_processing=post_processing,
        holdout_wape_score=metrics_after["wape_score"],
        submission_id=submission_id,
    )
    print(f"Manifest: {manifest_path} (submission_id={submission_id})")

    # 7. Convenience alias predictions/submission.csv (R3 clinerule 23) — не source-of-truth
    alias = output.parent / "submission.csv"
    alias.write_text(output.read_text())
    print(f"Alias: {alias} (convenience, NOT source-of-truth)")

    # 8. SUBMISSION CANDIDATE block (T-149, clinerule 24)
    print_candidate(
        csv_path=output,
        manifest_path=manifest_path,
        model_id=args.model_id,
        submission_id=submission_id,
        holdout_wape=metrics_after["wape_score"],
        submission_start=args.start_date,
        submission_end=args.end_date,
        row_count=len(grid),
        total_predictions=float(grid["prediction"].sum()),
        expected_rows=expected_rows,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
