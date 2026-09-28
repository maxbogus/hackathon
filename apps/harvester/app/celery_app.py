"""Celery application factory.

Broker: Redis (тот же что и для cache в apps/backend).
Backend: Redis (результаты задач храним 1 час).

Использование:
    celery -A app.celery_app:celery_app worker --loglevel=info
    uv run --package transit-ai-harvester celery -A app.celery_app:celery_app worker -l info
"""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "transit-ai-harvester",
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
    task_time_limit=300,  # 5 минут на задачу
    task_soft_time_limit=240,  # soft warning за 4 минуты
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
    # T-235: выделенная очередь (иначе делит default с ml_pipeline -> NotRegistered, F-141)
    task_default_queue="harvester",
    task_routes={"harvester.*": {"queue": "harvester"}},
)
