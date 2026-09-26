#!/usr/bin/env python3
"""Ablation analysis (T-175, F-049).

Train XGBoost с разными feature flags, оценить holdout WAPE-score.
Результат -> CSV + MD report.

Usage:
    uv run --directory ml python scripts/ablation.py
        --output docs/reports/ablation_2026-09-26.csv
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from transit_ai.config.flags import FlagsRegistry
from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource
from transit_ai.models.xgboost_route import XGBoostRoutePredictor
from transit_ai.reports.metrics import compute_metrics

SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
REPO_ROOT = ML_DIR.parent
CONFIG_DIR = ML_DIR / "transit_ai" / "config"

DEFAULT_TRAIN_START = datetime(2025, 1, 1, tzinfo=UTC)
DEFAULT_TRAIN_END = datetime(2025, 8, 31, tzinfo=UTC)
DEFAULT_HOLDOUT_START = datetime(2025, 9, 1, tzinfo=UTC)
DEFAULT_HOLDOUT_END = datetime(2025, 10, 31, tzinfo=UTC)

# Variants to test (по убыванию сложности)
VARIANTS = [
    ("full", "defaults.yaml"),
    ("with_traffic", "variants/with_traffic.yaml"),
    ("no_events", "variants/no_events.yaml"),
    ("no_poi", "variants/no_poi.yaml"),
    ("no_external", "variants/no_external.yaml"),
    ("base_only", "variants/base_only.yaml"),
]


def run_variant(
    name: str,
    yaml_path: Path,
    train_start: datetime,
    train_end: datetime,
    holdout_start: datetime,
    holdout_end: datetime,
) -> dict[str, float | str]:
    """Train XGBoost с заданными flags, evaluate на holdout."""
    print(f"\n--- Variant: {name} ({yaml_path.name}) ---")
    registry = FlagsRegistry.from_yaml(yaml_path)
    flags = registry.features

    src = RealSource()
    df = src.load_ridership(DateRange(train_start, holdout_end))
    train_mask = df["timestamp"] < pd.Timestamp(holdout_start).tz_localize(None)
    train_df = df[train_mask].copy()
    holdout_df = df[~train_mask].copy()

    model = XGBoostRoutePredictor(model_id=f"ablation_{name}")
    model.fit(df, flags=flags)

    # Build lag_lookup for inference
    from transit_ai.models.xgboost_route import build_lag_lookup

    lag_lookup = build_lag_lookup(train_df)

    preds = model.predict_batch(holdout_df, lag_lookup=lag_lookup)
    metrics = compute_metrics(holdout_df["boardings"].values, preds)
    print(f"  holdout WAPE-score = {metrics['wape_score']:.4f} (raw)")

    return {
        "variant": name,
        "yaml": yaml_path.name,
        "n_features": len(model.feature_names_),
        "use_geo_features": flags.use_geo_features,
        "use_poi_features": flags.use_poi_features,
        "use_events": flags.use_events,
        "use_traffic": flags.use_traffic,
        "use_seasonal_calendar": flags.use_seasonal_calendar,
        "use_weather": flags.use_weather,
        "use_validators_lookup": flags.use_validators_lookup,
        "wape_score_raw": metrics["wape_score"],
        "wape_raw": metrics["wape"],
        "mae": metrics["mae"],
        "rmsle": metrics["rmsle"],
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--output",
        default="docs/reports/ablation_2026-09-26.csv",
        help="Path to output CSV",
    )
    p.add_argument(
        "--variants",
        nargs="+",
        default=None,
        help="Subset of variant names (default: all)",
    )
    args = p.parse_args()

    output_csv = REPO_ROOT / args.output
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Ablation analysis (T-175)")
    print("=" * 60)

    results = []
    selected = args.variants if args.variants else [v[0] for v in VARIANTS]
    for name, yaml_rel in VARIANTS:
        if name not in selected:
            continue
        yaml_path = CONFIG_DIR / yaml_rel
        if not yaml_path.exists():
            print(f"  SKIP {name}: {yaml_path} not found")
            continue
        try:
            r = run_variant(
                name,
                yaml_path,
                DEFAULT_TRAIN_START,
                DEFAULT_TRAIN_END,
                DEFAULT_HOLDOUT_START,
                DEFAULT_HOLDOUT_END,
            )
            results.append(r)
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            results.append(
                {
                    "variant": name,
                    "yaml": yaml_rel,
                    "error": str(e),
                    "wape_score_raw": -1.0,
                }
            )

    # Save CSV
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_csv, index=False)
    print(f"\nResults saved to: {output_csv}")

    # Save MD report
    md_path = output_csv.with_suffix(".md")
    with md_path.open("w") as f:
        f.write("# Ablation Report\n\n")
        f.write(f"Generated: {datetime.now(UTC).isoformat()}\n\n")
        f.write("Holdout period: 2025-09-01 -> 2025-10-31 (sep-oct)\n\n")
        f.write("| Variant | Features | WAPE-score | MAE | RMSLE |\n")
        f.write("|---------|----------|------------|-----|-------|\n")
        for r in results:
            if "error" in r:
                f.write(f"| {r['variant']} | - | ERROR: {r['error']} | - | - |\n")
            else:
                f.write(
                    f"| {r['variant']} | {r['n_features']} | "
                    f"{r['wape_score_raw']:.4f} | {r['mae']:.1f} | {r['rmsle']:.4f} |\n"
                )
        f.write("\n## F-049 Interpretation\n\n")
        f.write("- **full** = baseline (v9_events equivalent), expected 0.9051\n")
        f.write("- **with_traffic** = +3 traffic features, expected +0-Xpp\n")
        f.write("- **no_events** = -4 event features, expected slightly lower\n")
        f.write("- **no_poi** = -15 POI features, expected lower\n")
        f.write("- **no_external** = -7 external (school/weather/validators)\n")
        f.write("- **base_only** = only 11 base features, expect lowest\n\n")
        f.write("Higher = better. Differences <0.005 are noise.\n")
    print(f"Report saved to: {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
