"""Celery tasks для ML pipeline.

Доступные задачи:
  - train_xgboost_task(model_id): обучение XGBoost
  - predict_window_task(model_id, from_date, to_date, feature_set, zeros)
  - apply_calibration_task(submission_id, weather, event, season)
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess

from celery import shared_task

from app.config import settings
from app.ml_cli import (
    build_flags_payload,
    build_predict_args,
    build_zero_args,
    write_flags_file,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _run_uv_script(script: str, *args: str) -> tuple[int, str, str]:
    """Run uv-managed ML script. Returns (returncode, stdout, stderr)."""
    cmd = [
        "uv",
        "--directory",
        str(settings.repo_root / "ml"),
        "run",
        "python",
        script,
        *args,
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
    feature_flags: dict | None = None,
    zero_overrides: dict | None = None,
    model_kind: str = "xgboost_route",
) -> dict:
    """Generate predictions for [start_date, end_date] using given model.

    Пишет в predictions/<unique>.csv + manifest.json (clinerule 23).

    Параметры (T-229 — «параметры генерации» из UI):
      - feature_flags: {use_poi: bool, ...} → flags.yaml (T-174)
      - zero_overrides: {zero_route_5: {}, zero_night_pred_cap: {pred_cap, hours}} → CLI
      - coef_weather/event/season: корректирующие коэффициенты (clinerule 24)
      - zeros: legacy-флаг (--apply-zeros), используется если zero_overrides пуст
    """
    flags_file = None
    payload = build_flags_payload(feature_flags)
    if payload is not None:
        flags_file = write_flags_file(
            settings.repo_root / "ml" / "tmp" / f"flags_{submission_id or 'adhoc'}.yaml",
            payload,
        )

    zero_args = build_zero_args(zero_overrides)
    if not zero_args and zeros:
        zero_args = [
            "--zero-route",
            "5",
            "--pred-cap",
            "55",
            "--cap-hours",
            "0",
            "1",
            "2",
            "3",
            "4",
        ]

    args = build_predict_args(
        model_id=model_id,
        start_date=start_date,
        end_date=end_date,
        submission_id=submission_id,
        coef_weather=coef_weather,
        coef_event=coef_event,
        coef_season=coef_season,
        model_kind=model_kind,
        flags_file=flags_file,
        zero_args=zero_args,
    )
    rc, out, err = _run_uv_script("scripts/make_submission.py", *args)
    if rc != 0:
        return {
            "status": "error",
            "returncode": rc,
            "stderr": err[-2000:],
            "stdout": out[-2000:],
            "ts": _now_iso(),
        }
    manifest_path = _find_manifest(submission_id)
    return {
        "status": "ok",
        "model_id": model_id,
        "submission_id": submission_id,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "csv_path": str(manifest_path.with_suffix(".csv")) if manifest_path else None,
        "stdout_tail": out[-1000:],
        "ts": _now_iso(),
    }


def _find_manifest(submission_id: str | None) -> Path | None:
    """Самый новый manifest кандидата (backend затем читает его же)."""
    if not submission_id:
        return None
    candidates: list[tuple[float, Path]] = []
    for path in settings.predictions_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and data.get("submission_id") == submission_id:
            candidates.append((path.stat().st_mtime, path))
    return max(candidates)[1] if candidates else None


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
    feature_flags: dict | None = None,
    zero_overrides: dict | None = None,
    model_kind: str = "xgboost_route",
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
        feature_flags=feature_flags,
        zero_overrides=zero_overrides,
        model_kind=model_kind,
    )
    return {
        "status": "ok" if pred_res["status"] == "ok" else "partial",
        "train": train_res,
        "predict": pred_res,
        "ts": _now_iso(),
    }


# Примечание (T-230): persistence кандидата в `predictions` делает BACKEND
# (app/predictions_active.py) из shared volume predictions/ — worker только
# генерирует CSV+manifest (clinerule 10: ML не знает про схему БД).
