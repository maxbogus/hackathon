"""Celery tasks для ML pipeline.

Доступные задачи:
  - train_xgboost_task(model_id): обучение XGBoost
  - predict_window_task(model_id, from_date, to_date, feature_set, zeros)
  - apply_calibration_task(submission_id, weather, event, season)
"""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess

from celery import shared_task

from app.config import settings


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _run_uv_script(script: str, *args: str) -> tuple[int, str, str]:
    """Run uv-managed ML script. Returns (returncode, stdout, stderr)."""
    cmd = [
        "uv", "--directory", str(settings.repo_root / "ml"),
        "run", "python", script, *args,
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(settings.repo_root))
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1700, check=False)
    return proc.returncode, proc.stdout, proc.stderr


# ─────────────────────────── Train ─────────────────────────────────────


@shared_task(name="ml_pipeline.train_xgboost", bind=True, max_retries=1)
def train_xgboost_task(self, model_id: str | None = None) -> dict:
    """Train XGBoost model via ml/scripts/train_xgboost.py.

    Артефакты пишутся в ml/artifacts/<model_id>/ (clinerule 10-ml-as-scripts).
    """
    args = ["--train-start", "2025-01-01", "--train-end", "2025-08-31"]
    if model_id:
        args += ["--model-id", model_id]
    rc, out, err = _run_uv_script("scripts/train_xgboost.py", *args)
    if rc != 0:
        return {
            "status": "error",
            "returncode": rc,
            "stderr": err[-2000:],
            "stdout": out[-2000:],
            "ts": _now_iso(),
        }
    # tail of stdout содержит SUBMISSION CANDIDATE block + meta.json path
    return {
        "status": "ok",
        "model_id": model_id or "xgboost_v_default",
        "stdout_tail": out[-1000:],
        "ts": _now_iso(),
    }


# ─────────────────────────── Predict ───────────────────────────────────


@shared_task(name="ml_pipeline.predict_window", bind=True, max_retries=1)
def predict_window_task(
    self,
    model_id: str = "xgboost_v_default",
    start_date: str = "2025-11-01",
    end_date: str = "2025-12-31",
    submission_id: str | None = None,
    coef_weather: float = 1.0,
    coef_event: float = 1.0,
    coef_season: float = 1.0,
    zeros: bool = False,
) -> dict:
    """Generate predictions for [start_date, end_date] using given model.

    Пишет в predictions/<unique>.csv + manifest.json.
    Параметры:
      - coef_weather/event/season: корректирующие коэффициенты (clinerule 24)
      - zeros: применить zero-strategy (route 5 + night hours)
    """
    args = [
        "--model-id", model_id,
        "--start-date", start_date.replace("-", ""),
        "--end-date", end_date.replace("-", ""),
        "--coef-weather", str(coef_weather),
        "--coef-event", str(coef_event),
        "--coef-season", str(coef_season),
    ]
    if zeros:
        args.append("--apply-zeros")
    if submission_id:
        args += ["--submission-id", submission_id]
    rc, out, err = _run_uv_script("scripts/make_submission.py", *args)
    if rc != 0:
        return {
            "status": "error",
            "returncode": rc,
            "stderr": err[-2000:],
            "stdout": out[-2000:],
            "ts": _now_iso(),
        }
    return {
        "status": "ok",
        "model_id": model_id,
        "submission_id": submission_id,
        "stdout_tail": out[-1000:],
        "ts": _now_iso(),
    }


# ─────────────────────────── Pipeline (all-in-one) ─────────────────────


@shared_task(name="ml_pipeline.full_pipeline", bind=True)
def full_pipeline(
    self,
    start_date: str = "2025-11-01",
    end_date: str = "2025-12-31",
    submission_id: str | None = None,
    coef_weather: float = 1.0,
    coef_event: float = 1.0,
    coef_season: float = 1.0,
    zeros: bool = False,
) -> dict:
    """train → predict, последовательно. Возвращает агрегированный результат."""
    train_res = train_xgboost_task()
    if train_res["status"] != "ok":
        return {"status": "error", "stage": "train", "result": train_res}
    pred_res = predict_window_task(
        model_id=train_res["model_id"],
        start_date=start_date,
        end_date=end_date,
        submission_id=submission_id,
        coef_weather=coef_weather,
        coef_event=coef_event,
        coef_season=coef_season,
        zeros=zeros,
    )
    return {
        "status": "ok" if pred_res["status"] == "ok" else "partial",
        "train": train_res,
        "predict": pred_res,
        "ts": _now_iso(),
    }


# ─────────────────────────── Persistence to DB ─────────────────────────


def _persist_predictions_to_db(parquet_path: Path, model_id: str) -> dict:
    """Best-effort: read parquet и INSERT в predictions table (если доступна).

    Заглушка: реальный insert будет добавлен после T-194 (DB schema + alembic).
    Сейчас возвращает {'status': 'skipped', 'reason': 'no DB schema yet'}.
    """
    return {
        "status": "skipped",
        "reason": "T-194 (DB schema) not yet implemented",
        "parquet_path": str(parquet_path),
        "model_id": model_id,
    }

