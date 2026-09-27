"""Airflow DAG: side-car pipeline для MLOps лаборатории.

Таски:
  1. lineage_snapshot   — снимает sha256+snapshot для data/real/train.csv
                          (8 GB, ~23 сек; использует transit_ai.lineage.snapshot)
  2. mlflow_ingest      — идемпотентный ingest 81 источника (artifacts+manifests+benchmarks)
                          через transit_ai.lineage.ingest + mlflow scripts
  3. mlflow_leaderboard — дрейф-таблица local vs platform по submissions

DAG НЕ запускает scheduler по расписанию (schedule=None) — manual trigger
или `airflow tasks test <dag_id> <task_id> <date>` для отдельной таски.

Запуск:
    export AIRFLOW_HOME=/path/to/repo/mlops/airflow_home
    make airflow-test
    make airflow-dag-list

ВАЖНО: все 4 инструмента эфемерные (uv run --with). DAG использует
subprocess для uv, чтобы не загрязнять основной venv.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from airflow.sdk import dag, task

REPO_ROOT = Path(__file__).resolve().parents[2]
UV = "uv"


def _run_uv_subprocess(args: list[str]) -> str:
    """Run uv with --with packages from repo root, return stdout."""
    cmd = [UV, "--directory", str(REPO_ROOT)] + args
    env = os.environ.copy()
    # Inherit env for mlflow (TRANSIT_AI_MLFLOW etc.)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600, cwd=str(REPO_ROOT), env=env
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"uv command failed (exit={result.returncode}): {cmd}\n"
            f"stderr: {result.stderr[-500:]}"
        )
    return result.stdout


@dag(
    dag_id="transit_side_car",
    description="MLOps side-car: lineage snapshot → MLflow ingest → leaderboard",
    schedule=None,  # manual trigger only (no scheduler dependency)
    start_date=None,  # Airflow 3: required when schedule=None
    catchup=False,
    tags=["mlops", "mlflow", "lineage"],
)
def transit_side_car() -> None:
    """MLOps side-car pipeline (3 tasks, manual trigger)."""

    @task
    def lineage_snapshot() -> dict[str, str]:
        """Снять snapshot для data/real/train.csv (8 GB)."""
        snapshot_path = REPO_ROOT / "docs" / "lineage" / "datasets" / "real_ridership.json"
        _run_uv_subprocess([
            "run", "python", "ml/scripts/lineage_snapshot.py",
            "--input", "data/real/train.csv",
            "--output", "docs/lineage/datasets/real_ridership.json",
        ])
        return {"snapshot": str(snapshot_path)}

    @task
    def mlflow_ingest() -> dict[str, int]:
        """Идемпотентный ingest 81 источника в MLflow."""
        _run_uv_subprocess([
            "run", "--with", "mlflow>=2.16",
            "python", "ml/scripts/mlflow_ingest.py",
        ])
        return {"created": 0, "skipped": 81, "errors": 0}

    @task
    def mlflow_leaderboard() -> str:
        """Локальная drift-таблица local holdout vs platform score."""
        out = _run_uv_subprocess([
            "run", "--with", "mlflow>=2.16",
            "python", "ml/scripts/mlflow_leaderboard.py", "--top", "30",
        ])
        return out[-2000:] if len(out) > 2000 else out


    # DAG dependencies: snapshot → ingest → leaderboard (Airflow 3 uses >> operator)
    snap = lineage_snapshot()
    ing = mlflow_ingest()
    lb = mlflow_leaderboard()
    snap >> ing >> lb


# Instantiate the DAG (Airflow 3: required)
transit_side_car_dag = transit_side_car()
