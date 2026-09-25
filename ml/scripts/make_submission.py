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
    Shape: 10 routes × 61 days × 24 hours = 14 640 строк
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.route_baseline import RouteBaselineMean
from transit_ai.reports.metrics import compute_metrics

ROUTES: tuple[int, ...] = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)
DEFAULT_TRAIN_START = datetime(2025, 1, 1, tzinfo=UTC)
DEFAULT_TRAIN_END = datetime(2025, 8, 31, tzinfo=UTC)
DEFAULT_TEST_START = datetime(2025, 9, 1, tzinfo=UTC)
DEFAULT_TEST_END = datetime(2025, 10, 31, tzinfo=UTC)
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
    p.add_argument("--output", default=None, help="Output CSV path")
    args = p.parse_args()

    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=UTC)
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=UTC)

    print("=" * 60)
    print(f"Submission pipeline (T-145) — model: {args.model_id}")
    print("=" * 60)
    print(f"Date range: {args.start_date} → {args.end_date}")

    # 1. Load real data + train
    src = RealSource()
    train_df = src.load_ridership(DateRange(DEFAULT_TRAIN_START, DEFAULT_TRAIN_END))
    print(
        f"Train rows: {len(train_df):,} ({DEFAULT_TRAIN_START.date()} → {DEFAULT_TRAIN_END.date()})"
    )

    model = RouteBaselineMean(model_id=args.model_id)
    model.fit(train_df)
    print(f"Fit done: {len(model.table_)} (route, weekday, hour) buckets")

    # 2. Evaluate on test (holdout: sep-oct)
    test_df = src.load_ridership(DateRange(DEFAULT_TEST_START, DEFAULT_TEST_END))
    test_pred = model.predict_batch(test_df)
    metrics = compute_metrics(test_df["boardings"].values, test_pred)
    print()
    print(f"Holdout WAPE-score (сен–окт): {metrics['wape_score']:.4f}")
    print(
        f"  MAE={metrics['mae']:.1f}, WAPE={metrics['wape']:.4f}, RMSLE={metrics['rmsle']:.4f}"
    )

    # 3. Build full grid for submission
    grid, expected_rows = build_full_grid(start_dt, end_dt)
    print(f"Submission grid: {grid.shape} (expected {expected_rows} rows)")

    # 4. Predict each grid row
    # predict_batch expects route_id/date/hour cols (matching RealSource output)
    pred_df = grid.rename(columns={"route": "route_id"})
    pred_df["date"] = pd.to_datetime(pred_df["date"])
    preds = model.predict_batch(pred_df)

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

    grid["prediction"] = np.round(preds, 2)

    # 5. Save
    if args.output:
        output = Path(args.output)
    else:
        ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M")
        output = DEFAULT_OUTPUT_DIR / f"submission_{args.model_id}_{ts}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(output, sep=";", index=False)
    print(f"Saved to: {output}")
    print(f"Total rows: {len(grid)} (expected {expected_rows})")
    print(f"Total predictions: {grid['prediction'].sum():,.0f} boardings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
