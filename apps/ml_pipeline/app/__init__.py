"""Transit-AI ML Pipeline — Celery worker для обучения и инференса.

T-193: отдельный воркер, который:
  - train_xgboost_task: обучает XGBoost на данных из data/real/
    → артефакт в ml/artifacts/<model_id>/
  - predict_window_task: делает прогноз на указанное окно
    → пишет в predictions/<run_id>.parquet + INSERT в PostgreSQL

Переиспользует код из ml/transit_ai/* через uv workspace.
"""

from app.celery_app import celery_app

__all__ = ["celery_app"]
