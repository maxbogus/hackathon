"""Airflow DAG: transit_pipeline — оркестрация ML-пайплайна (T-235).

Единственный DAG проекта: старый side-car `transit_side_car` удалён, потому что
запускал шаги через `uv subprocess` — внутри контейнера Airflow это невозможно
(uv-окружения нет, `uv run` создаёт .venv и тянет GB-и, F-133).

Инвариант: ни одного импорта кода проекта (`app.*`, `transit_ai.*`) — только
Celery-задачи **по имени** через `_celery_client`. Благодаря этому DAG переносится
в общий Airflow без правок (меняется bundle, не код) и не тянет ML-зависимости.

Стадии:
  1. harvest_all        → harvester.fetch_all
  2. train_xgboost      → ml_pipeline.train_xgboost
  3. mlflow_ingest      → ml_pipeline.run_ml_script(script=mlflow_ingest)
  4. predict_window     → ml_pipeline.predict_window (+ YAML-профиль overrides)
  5. mlflow_leaderboard → ml_pipeline.run_ml_script(script=mlflow_leaderboard)

Запуск (schedule=None, только вручную):
    make airflow-trigger
    airflow dags trigger transit_pipeline --conf '{"model_id": "xgboost_v11_traffic"}'
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from _celery_client import send, wait  # sibling-модуль в mlops/dags (без celery на импорте)
from airflow.sdk import dag, task

PARTIAL_MODEL_ID = "xgboost_v11_traffic"
OVERRIDES_FILE = "ml/configs/overrides/nov_dec_2025.yaml"
OVERRIDES_PROFILE = "a_conservative"


def _run_celery(key: str, timeout: float, **kwargs: object) -> dict:
    """Отправить задачу по имени и дождаться результата (для XCom)."""
    handle = send(key, **kwargs)
    outcome = wait(handle, timeout=timeout)
    outcome["task_name"] = handle.task_name
    return outcome


def _default_submission_id() -> str:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"airflow-pilot-{stamp}"


@dag(
    dag_id="transit_pipeline",
    description="ML pipeline: harvest → train → mlflow ingest → predict → leaderboard",
    schedule=None,  # manual trigger only (демо/R4-safe)
    start_date=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},
    tags=["mlops", "pipeline", "transit"],
)
def transit_pipeline() -> None:
    """Оркестрация пайплайна: все шаги — Celery-задачи по имени."""

    @task(execution_timeout=timedelta(minutes=15))
    def harvest() -> dict:
        """Собрать внешние источники (local mode: raw → normalized)."""
        return _run_celery("harvest_all", timeout=600)

    @task(execution_timeout=timedelta(minutes=35), retries=1)
    def train(model_id: str = PARTIAL_MODEL_ID) -> dict:
        """Обучить XGBoost route-only (R6: ≤ 60 мин)."""
        return _run_celery("train_xgboost", timeout=1800, model_id=model_id)

    @task(execution_timeout=timedelta(minutes=20))
    def mlflow_ingest() -> dict:
        """Идемпотентный ingest артефактов/манифестов/бенчмарков в MLflow."""
        return _run_celery("run_ml_script", timeout=900, script="mlflow_ingest")

    @task(execution_timeout=timedelta(minutes=35), retries=1)
    def predict(
        model_id: str = PARTIAL_MODEL_ID,
        submission_id: str = "",
        overrides_file: str = OVERRIDES_FILE,
        overrides_profile: str = OVERRIDES_PROFILE,
    ) -> dict:
        """Сгенерировать submission (clinerule 23) с schedule-overrides профиля."""
        kwargs: dict[str, object] = {
            "model_id": model_id,
            "submission_id": submission_id or _default_submission_id(),
            "overrides_file": overrides_file,
            "overrides_profile": overrides_profile,
        }
        return _run_celery("predict_window", timeout=1800, **kwargs)

    @task(execution_timeout=timedelta(minutes=20))
    def leaderboard() -> dict:
        """Drift-таблица local holdout vs platform score."""
        return _run_celery("run_ml_script", timeout=900, script="mlflow_leaderboard")

    harvest() >> train() >> mlflow_ingest() >> predict() >> leaderboard()


transit_pipeline_dag = transit_pipeline()
