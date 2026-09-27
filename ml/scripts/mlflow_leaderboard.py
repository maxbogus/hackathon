#!/usr/bin/env python3
"""Leaderboard: local holdout vs platform score по всем submissions.

Читает MLflow-раны (transit_ai.source = submission-manifest) и строит таблицу:
  submission_id | holdout_wape_score | platform_score | drift
с сортировкой по holdout (лучший сверху).

Это ДРЕЙФ-ТАБЛИЦА: одна строка = один сабмит, видно drift = platform - holdout.
Заменяет ручной grep по docs/ledger/findings.jsonl.

Usage:
    make mlflow-leaderboard
    cd ml && uv run --with mlflow python scripts/mlflow_leaderboard.py
    cd ml && uv run --with mlflow python scripts/mlflow_leaderboard.py --top 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from transit_ai.tracking import experiment_name, is_enabled, tracking_uri  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Local holdout vs platform leaderboard")
    parser.add_argument("--top", type=int, default=30, help="показать top-N (default 30)")
    parser.add_argument("--all", action="store_true", help="показать все")
    args = parser.parse_args()

    if not is_enabled():
        print("MLflow выключен. Включить: uv run --with mlflow ...")
        return 1

    import mlflow

    mlflow.set_tracking_uri(tracking_uri())
    runs = mlflow.search_runs(
        experiment_names=[experiment_name()],
        filter_string="tags.transit_ai.source = 'submission-manifest'",
        max_results=1000,
        order_by=["metrics.holdout_wape_score DESC"],
    )

    if runs.empty:
        print("Нет submission-манифестов. Сначала: make mlflow-ingest --only manifests")
        return 0

    # Колонки
    sub_col = "params.submission_id"
    model_col = "params.model_id"
    holdout_col = "metrics.holdout_wape_score"
    platform_col = "metrics.platform_score"
    drift_col = "metrics.drift_wape_score"
    submitted_col = "tags.transit_ai.platform_submitted"
    git_col = "params.git_commit"

    print(f"experiment: {experiment_name()}")
    print(f"submissions: {len(runs)}")
    print()

    # Header
    print(f"{'submission_id':<40} {'model':<30} {'holdout':>8} {'platform':>9} "
          f"{'drift':>8} {'submitted':>10} {'git':>9}")
    print("-" * 120)

    limit = len(runs) if args.all else args.top
    for _, r in runs.head(limit).iterrows():
        sub = str(r.get(sub_col, ""))[:39]
        model = str(r.get(model_col, ""))[:29]
        holdout = r.get(holdout_col, None)
        platform = r.get(platform_col, None)
        drift = r.get(drift_col, None)
        submitted = str(r.get(submitted_col, "?"))
        git = str(r.get(git_col, ""))[:8]

        def fmt(v):
            if v is None or (isinstance(v, float) and v != v):  # NaN check
                return "    -"
            if isinstance(v, float):
                return f"{v:8.4f}"
            return f"{v:>8}"

        print(f"{sub:<40} {model:<30} {fmt(holdout):>8} {fmt(platform):>9} "
              f"{fmt(drift):>8} {submitted:>10} {git:>9}")

    # Статистика
    submitted_count = 0
    if platform_col in runs.columns:
        submitted_count = int(runs[platform_col].notna().sum())

    print()
    print(f"submitted to platform: {submitted_count}/{len(runs)}")
    if platform_col in runs.columns and holdout_col in runs.columns:
        both = runs[[holdout_col, platform_col]].dropna()
        if len(both) > 0:
            avg_drift = (both[platform_col] - both[holdout_col]).mean()
            print(f"avg drift (platform - holdout): {avg_drift:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
