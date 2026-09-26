"""Smoke test for ml_pipeline Celery app."""

from __future__ import annotations

from app.celery_app import celery_app
from app.tasks import _persist_predictions_to_db, _run_uv_script


def test_celery_app_has_tasks() -> None:
    """Ensure all expected tasks are registered."""
    registered = set(celery_app.tasks.keys())
    assert "ml_pipeline.train_xgboost" in registered
    assert "ml_pipeline.predict_window" in registered
    assert "ml_pipeline.full_pipeline" in registered


def test_run_uv_script_returns_tuple() -> None:
    """Smoke: uv call to a real script."""
    rc, out, err = _run_uv_script(
        "scripts/make_submission.py",
        "--help",
    )
    # --help exits 0; allow nonzero for parser errors but never raise
    assert isinstance(rc, int)
    assert isinstance(out, str)
    assert isinstance(err, str)


def test_persist_predictions_to_db_stub(tmp_path) -> None:
    res = _persist_predictions_to_db(tmp_path / "nope.parquet", "xgboost_v1")
    assert res["status"] == "skipped"
    assert "T-194" in res["reason"]
