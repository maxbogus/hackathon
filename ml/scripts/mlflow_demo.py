#!/usr/bin/env python3
"""Демо MLflow tracking: 3 синтетических конфига × 4 fold → раны в локальном store.

Ничего не обучает и не требует данных — только показывает, как выглядит tracking
(родительский ран + nested fold-раны + артефакт).

Usage:
    make mlflow-demo
    cd ml && uv run --with "mlflow>=2.16" python scripts/mlflow_demo.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ml/
sys.path.insert(0, str(ROOT))

from transit_ai.tracking import track_run  # noqa: E402

SEED = 42
FOLDS = 4
CONFIGS: list[dict[str, object]] = [
    {
        "model_id": "xgboost_demo",
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.10,
        "_base": 0.8800,
    },
    {
        "model_id": "xgboost_demo",
        "n_estimators": 500,
        "max_depth": 8,
        "learning_rate": 0.05,
        "_base": 0.8855,
    },
    {
        "model_id": "gru_demo",
        "hidden_dim": 128,
        "num_layers": 2,
        "seq_len": 336,
        "_base": 0.8790,
    },
]


def main() -> int:
    rng = random.Random(SEED)
    if not track_run:
        return 1
    with track_run(
        "mlflow-demo",
        params={"n_configs": len(CONFIGS), "folds": FOLDS, "seed": SEED},
        tags={"transit_ai.source": "mlflow_demo"},
    ) as parent:
        print(parent.summary_line())
        if not parent.enabled:
            print("Подсказка: make mlflow-demo (ставит mlflow эфемерно)\n")
            return 0

        best = -1.0
        for idx, raw in enumerate(CONFIGS):
            cfg = {k: v for k, v in raw.items() if not k.startswith("_")}
            base = float(raw["_base"])
            folds = [round(base + rng.uniform(-0.02, 0.02), 4) for _ in range(FOLDS)]
            mean_score = round(sum(folds) / len(folds), 4)
            best = max(best, mean_score)
            with track_run(f"{cfg['model_id']}-{idx}", params=cfg, nested=True) as run:
                run.log_metrics(
                    {
                        "wape_score": mean_score,
                        "platform_score": round(mean_score - 0.06, 4),
                    }
                )
                run.log_folds(folds, metric="wape_score")
                print(
                    f"  {run.name:20} wape_score={mean_score:.4f} "
                    f"folds={folds} run_id={run.run_id}"
                )

        parent.log_metrics({"best_wape_score": best})
        parent.log_json(
            {"demo": True, "configs": len(CONFIGS), "best_wape_score": best},
            "demo_summary.json",
        )
    print("\nСмотреть: make mlflow-runs  |  make mlflow-ui → http://127.0.0.1:5000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
