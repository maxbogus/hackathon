#!/usr/bin/env python3
"""Список MLflow-ранов из локального store (CLI-альтернатива UI).

Usage:
    make mlflow-runs
    LIMIT=50 make mlflow-runs
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ml/
sys.path.insert(0, str(ROOT))

from transit_ai.tracking import experiment_name, is_enabled, tracking_uri  # noqa: E402

PREFERRED_COLUMNS = (
    "tags.mlflow.runName",
    "metrics.wape_score",
    "metrics.platform_score",
    "metrics.fold_mean_wape_score",
    "metrics.fold_mean_rmsle",
    "tags.transit_ai.git_commit",
    "tags.transit_ai.status",
)


def main() -> int:
    if not is_enabled():
        print("MLflow недоступен/выключен. Запуск: make mlflow-runs (эфемерный env)")
        return 1

    import mlflow

    mlflow.set_tracking_uri(tracking_uri())
    limit = int(os.environ.get("LIMIT", "20"))
    runs = mlflow.search_runs(
        experiment_names=[experiment_name()],
        max_results=limit,
        order_by=["start_time DESC"],
    )
    if runs.empty:
        print("Ранов нет. Сначала: make mlflow-demo")
        return 0

    name_col = "tags.mlflow.runName"
    if name_col in runs.columns:
        # fold-* — служебные nested-раны, в таблицу не выводим
        keep = ~runs[name_col].astype(str).str.startswith("fold-")
        runs = runs[keep]

    columns = [c for c in PREFERRED_COLUMNS if c in runs.columns]
    print(f"store={tracking_uri()}")
    print(f"experiment={experiment_name()}, runs={len(runs)}\n")
    print(runs[columns].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
