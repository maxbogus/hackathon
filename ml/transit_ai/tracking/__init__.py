"""Опциональный MLflow tracking для ML-скриптов (observability, не источник истины).

См. docs/MLFLOW.md и .clinerules/10-ml-as-scripts.md.
"""

from transit_ai.tracking.mlflow_tracker import (
    DEFAULT_EXPERIMENT,
    DEFAULT_TRACKING_URI,
    RunTracker,
    experiment_name,
    is_enabled,
    track_run,
    tracking_uri,
)

__all__ = [
    "DEFAULT_EXPERIMENT",
    "DEFAULT_TRACKING_URI",
    "RunTracker",
    "experiment_name",
    "is_enabled",
    "track_run",
    "tracking_uri",
]
