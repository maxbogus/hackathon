"""Тонкий Celery-клиент для оркестрации (T-235).

Зачем: Airflow-DAG и Makefile должны ставить задачи в существующие воркеры
(`harvester` / `ml_pipeline`) **по имени**, не импортируя их код. Импорт `app.*`
ломался (в venv три пакета `app`: assistant / harvester / ml_pipeline — `import app`
резолвился в assistant, F-127) и тянул бы ML-зависимости в оркестратор.

Контракт: имя задачи + kwargs → ``task_id``; ожидание — polling ``AsyncResult``.
Реестр ``TASKS`` — allowlist: произвольные имена не отправляем.

Использование::

    from mlops.dags._celery_client import send, wait

    handle = send("train_xgboost", model_id="xgboost_v11_traffic")
    print(wait(handle, timeout=1800))
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Any, Protocol

DEFAULT_BROKER = "redis://localhost:6379/1"
DEFAULT_BACKEND = "redis://localhost:6379/2"

# Allowlist: ключ → имя задачи в воркере. DAG/CLI работают только с ключами.
TASKS: dict[str, str] = {
    "harvest_all": "harvester.fetch_all",
    "harvest_weather": "harvester.fetch_weather_json",
    "train_xgboost": "ml_pipeline.train_xgboost",
    "predict_window": "ml_pipeline.predict_window",
    "full_pipeline": "ml_pipeline.full_pipeline",
    "run_ml_script": "ml_pipeline.run_ml_script",
}

TERMINAL_STATES = frozenset({"SUCCESS", "FAILURE", "REVOKED"})


class CeleryLike(Protocol):
    """Минимальный интерфейс Celery, который нужен клиенту (для тестов)."""

    def send_task(self, name: str, kwargs: dict[str, Any] | None = ...) -> Any:  # noqa: ANN401
        ...


@dataclass(frozen=True)
class TaskHandle:
    """Отправленная задача: id + фактическое имя в воркере."""

    task_id: str
    task_name: str
    key: str


def broker_url() -> str:
    """Broker URL (env TRANSIT_AI_CELERY_BROKER / CELERY_BROKER_URL)."""
    return (
        os.environ.get("TRANSIT_AI_CELERY_BROKER")
        or os.environ.get("CELERY_BROKER_URL")
        or DEFAULT_BROKER
    )


def backend_url() -> str:
    """Result backend URL (env TRANSIT_AI_CELERY_BACKEND / CELERY_RESULT_BACKEND)."""
    return (
        os.environ.get("TRANSIT_AI_CELERY_BACKEND")
        or os.environ.get("CELERY_RESULT_BACKEND")
        or DEFAULT_BACKEND
    )


def make_client() -> Any:  # noqa: ANN401 (celery.Celery — динамический API)
    """Создать Celery-клиент (без импорта кода воркеров)."""
    from celery import Celery  # noqa: PLC0415 (lazy: AST-проверкам DAG celery не нужен)

    return Celery("transit-orchestrator", broker=broker_url(), backend=backend_url())


def resolve_task_name(key: str) -> str:
    """Ключ allowlist → имя задачи в воркере.

    Raises:
        KeyError: ключа нет в реестре (со списком доступных).
    """
    if key not in TASKS:
        raise KeyError(f"задача {key!r} не в реестре; доступны: {sorted(TASKS)}")
    return TASKS[key]


def queue_for(task_name: str) -> str:
    """Очередь для задачи: префикс имени модуля (harvester/ml_pipeline — F-141).

    Воркеры слушают свои очереди (task_default_queue), поэтому задача не может
    достаться чужому воркеру и получить NotRegistered.
    """
    return task_name.split(".", 1)[0]


def send(
    key: str,
    client: CeleryLike | None = None,
    **kwargs: Any,  # noqa: ANN401 (kwargs задачи прокидываются как есть)
) -> TaskHandle:
    """Отправить задачу из allowlist в брокер (не блокирует).

    Args:
        key: ключ из ``TASKS``.
        client: инъекция Celery-клиента (для тестов); по умолчанию ``make_client()``.
        **kwargs: аргументы задачи (передаются как kwargs).

    Returns:
        ``TaskHandle`` с task_id.
    """
    task_name = resolve_task_name(key)
    celery_client = client if client is not None else make_client()
    async_result = celery_client.send_task(
        task_name, kwargs=kwargs or None, queue=queue_for(task_name)
    )
    return TaskHandle(task_id=str(async_result.id), task_name=task_name, key=key)


def wait(
    handle: TaskHandle,
    timeout: float = 600.0,
    poll_interval: float = 1.0,
    client: CeleryLike | None = None,
) -> dict[str, Any]:
    """Дождаться завершения задачи (polling AsyncResult.state).

    Args:
        handle: результат ``send()``.
        timeout: максимум секунд ожидания.
        poll_interval: период опроса.
        client: инъекция клиента (по умолчанию ``make_client()``).

    Returns:
        ``{"task_id": ..., "state": "SUCCESS"|..., "result": ...|None}``.
        При таймауте state = "TIMEOUT" (не бросаем — решение за вызывающим).
    """
    celery_client = client if client is not None else make_client()
    result = celery_client.AsyncResult(handle.task_id)  # type: ignore[attr-defined]
    deadline = time.monotonic() + float(timeout)
    while True:
        state = str(result.state)
        if state in TERMINAL_STATES:
            payload: Any = result.result if state == "SUCCESS" else None
            return {"task_id": handle.task_id, "state": state, "result": payload}
        if time.monotonic() >= deadline:
            return {"task_id": handle.task_id, "state": "TIMEOUT", "result": None}
        time.sleep(poll_interval)


__all__ = [
    "DEFAULT_BACKEND",
    "DEFAULT_BROKER",
    "TASKS",
    "TERMINAL_STATES",
    "TaskHandle",
    "backend_url",
    "broker_url",
    "make_client",
    "queue_for",
    "resolve_task_name",
    "send",
    "wait",
]
