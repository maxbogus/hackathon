#!/usr/bin/env python3
"""Profile hackathon real dataset -> data/validation_reports/inventory.json (R8).

Validation report для хакатона:
  * Размеры (rows, total boardings)
  * Routes / hours / date range покрытие
  * Per-route / per-hour stats
  * Sanity checks (нет пропусков, формат OK)

Usage:
    make inventory   # = uv run --directory ml python scripts/inventory.py

Output:
    data/validation_reports/inventory.json (R8 deliverable)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from transit_ai.data.base import DateRange
from transit_ai.data.real import RealSource

ROOT = Path(__file__).resolve().parents[1]  # ml/
REPO_ROOT = ROOT.parent
DEFAULT_LABELS_DIR = REPO_ROOT / "data" / "real" / "labels"
DEFAULT_OUT = REPO_ROOT / "data" / "validation_reports" / "inventory.json"

EXPECTED_ROUTES = {1, 5, 7, 11, 12, 17, 25, 26, 28, 50}  # F-045: 10 routes including route 5
EXPECTED_HOURS = set(range(24))


def _sha256_concat(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.read_bytes())
        h.update(b"\n")
    return h.hexdigest()


def _per_route(full):
    by_route = full.groupby("route_id").agg(
        rows=("boardings", "size"),
        total=("boardings", "sum"),
        mean=("boardings", "mean"),
        median=("boardings", "median"),
        max=("boardings", "max"),
        min=("boardings", "min"),
        std=("boardings", "std"),
    )
    out = {}
    for rid, row in by_route.iterrows():
        std_val = float(row["std"]) if row["std"] == row["std"] else 0.0
        out[str(int(rid))] = {
            "rows": int(row["rows"]),
            "total_boardings": int(row["total"]),
            "mean_per_hour": float(row["mean"]),
            "median_per_hour": float(row["median"]),
            "max_hour": int(row["max"]),
            "min_hour": int(row["min"]),
            "std": std_val,
        }
    return out


def _per_hour(full):
    by_hour = full.groupby("hour")["boardings"].agg(["sum", "mean", "count"])
    out = {}
    for h, row in by_hour.iterrows():
        out[str(int(h))] = {
            "total_boardings": int(row["sum"]),
            "mean": float(row["mean"]),
            "rows": int(row["count"]),
        }
    return out


def _per_month(full):
    full = full.copy()
    full["month"] = full["date"].dt.to_period("M").astype(str)
    by_month = full.groupby("month").size()
    return {m: int(c) for m, c in by_month.items()}


def main():
    p = argparse.ArgumentParser(description="Generate inventory.json for hackathon R8.")
    p.add_argument("--labels-dir", type=Path, default=DEFAULT_LABELS_DIR)
    p.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    p.add_argument("--from-date", default="2025-01-01")
    p.add_argument("--to-date", default="2025-10-31")
    args = p.parse_args()

    labels_dir = args.labels_dir
    if not (labels_dir / "labels_day_train.csv").exists():
        print("ERROR: Labels not found: " + str(labels_dir), file=sys.stderr)
        return 1

    out_path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("[inventory] Loading real dataset...", file=sys.stderr)
    src = RealSource(labels_dir=labels_dir)
    full = src.load_ridership(
        DateRange(
            datetime.fromisoformat(args.from_date).replace(tzinfo=UTC),
            datetime.fromisoformat(args.to_date).replace(tzinfo=UTC),
        )
    )

    routes_seen = set(int(r) for r in full["route_id"].unique())
    hours_seen = set(int(h) for h in full["hour"].unique())
    missing_routes = sorted(EXPECTED_ROUTES - routes_seen)
    missing_hours = sorted(EXPECTED_HOURS - hours_seen)

    label_files = sorted(labels_dir.glob("labels_day_*.csv"))
    dataset_hash = _sha256_concat(label_files)

    inventory = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "RealSource (hackathon)",
        "labels_dir": str(labels_dir.relative_to(REPO_ROOT)),
        "label_files": [str(f.relative_to(REPO_ROOT)) for f in label_files],
        "dataset_hash_sha256": dataset_hash,
        "expected_routes": sorted(EXPECTED_ROUTES),
        "expected_hours": sorted(EXPECTED_HOURS),
        "date_range": {
            "min": str(full["date"].min().date()),
            "max": str(full["date"].max().date()),
        },
        "totals": {
            "rows": int(len(full)),
            "total_boardings": int(full["boardings"].sum()),
            "mean_boardings_per_hour": float(full["boardings"].mean()),
            "median_boardings_per_hour": float(full["boardings"].median()),
            "max_boardings_per_hour": int(full["boardings"].max()),
        },
        "coverage": {
            "routes_seen": sorted(routes_seen),
            "hours_seen": sorted(hours_seen),
            "missing_routes": missing_routes,
            "missing_hours": missing_hours,
            "all_routes_present": len(missing_routes) == 0,
            "all_hours_present": len(missing_hours) == 0,
        },
        "per_route": _per_route(full),
        "per_hour": _per_hour(full),
        "per_month_rows": _per_month(full),
        "sanity_checks": {
            "no_nulls": bool(full.notna().all().all()),
            "all_boardings_non_negative": bool((full["boardings"] >= 0).all()),
            "notes": [],
        },
    }

    notes = inventory["sanity_checks"]["notes"]
    if missing_routes:
        notes.append("Missing routes: " + str(missing_routes) + " (cold-start candidates: zero prediction).")
    if missing_hours:
        notes.append("Missing hours: " + str(missing_hours))
    if not inventory["sanity_checks"]["no_nulls"]:
        notes.append("Null values present in dataset.")
    if not inventory["sanity_checks"]["all_boardings_non_negative"]:
        notes.append("Negative boardings detected (data corruption?).")

    out_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[inventory] OK: " + str(out_path), file=sys.stderr)
    print(
        "[inventory] rows=" + str(inventory["totals"]["rows"])
        + ", routes=" + str(len(routes_seen))
        + ", hours=" + str(len(hours_seen))
        + ", missing_routes=" + str(missing_routes),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
