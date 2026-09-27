"""Smoke test for ml_pipeline Celery app."""

from __future__ import annotations

from app.celery_app import celery_app
from app.tasks import _find_manifest, _run_uv_script


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


def test_find_manifest_returns_none_without_submission_id() -> None:
    """T-230: без submission_id искать нечего → None (не падаем)."""
    assert _find_manifest(None) is None
    assert _find_manifest("") is None
