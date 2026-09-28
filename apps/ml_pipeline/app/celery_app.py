"""Celery application factory."""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "transit-ai-ml-pipeline",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 минут (R6 hackathon-rules: train ≤ 60 мин)
    task_soft_time_limit=1500,
    worker_max_tasks_per_child=10,
    worker_prefetch_multiplier=1,
    # T-235: выделенная очередь. Без неё harvester и ml_pipeline делят default-очередь,
    # и ml_pipeline-задача может достаться harvester-воркеру -> NotRegistered (F-141).
    task_default_queue="ml_pipeline",
    task_routes={"ml_pipeline.*": {"queue": "ml_pipeline"}},
)
