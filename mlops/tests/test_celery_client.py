"""Tests for mlops/dags/_celery_client.py (T-235).

Проверяем тонкую обёртку над Celery без реального брокера:
  - allowlist задач (ключ → имя в воркере) и понятная ошибка на неизвестный ключ
  - send() шлёт задачу по имени, kwargs доходят как kwargs, возвращается task_id
  - wait() крутит polling до терминального состояния и не виснет на TIMEOUT
  - broker/backend читаются из env (переопределяемость под Docker-сеть)
  - имена задач принадлежат существующим воркерам (harvester / ml_pipeline)
"""

from __future__ import annotations

from typing import Any

import pytest

from mlops.dags import _celery_client as cc


class _FakeAsyncResult:
    """AsyncResult с заранее заданной последовательностью состояний."""

    def __init__(self, states: list[str], result: Any = None) -> None:
        self._states = states
        self._result = result
        self._index = 0

    @property
    def state(self) -> str:
        state = self._states[min(self._index, len(self._states) - 1)]
        self._index += 1
        return state

    @property
    def result(self) -> Any:
        return self._result


class _FakeCelery:
    """Минимальный Celery-двойник: пишет вызовы и отдаёт AsyncResult."""

    def __init__(self, states: list[str] | None = None, result: Any = None) -> None:
        self.sent: list[tuple[str, dict[str, Any] | None]] = []
        self._states = states or ["SUCCESS"]
        self._result = result
        self.last_task_id = ""

    def send_task(self, name: str, kwargs: dict[str, Any] | None = None) -> Any:
        self.sent.append((name, kwargs))
        self.last_task_id = f"fake-{len(self.sent)}"
        return type("_AR", (), {"id": self.last_task_id})()

    def AsyncResult(self, task_id: str) -> _FakeAsyncResult:  # noqa: N802 (celery API)
        return _FakeAsyncResult(self._states, self._result)


# ─────────────────────────── allowlist / env ───────────────────────────


def test_registry_maps_keys_to_worker_task_names() -> None:
    """Ключи реестра указывают на задачи реальных воркеров."""
    for name in cc.TASKS.values():
        assert name.startswith(("harvester.", "ml_pipeline.")), name


def test_resolve_task_name_known_and_unknown() -> None:
    assert cc.resolve_task_name("train_xgboost") == "ml_pipeline.train_xgboost"
    with pytest.raises(KeyError, match="train_xgboost"):
        cc.resolve_task_name("nope")


def test_broker_and_backend_come_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRANSIT_AI_CELERY_BROKER", raising=False)
    monkeypatch.delenv("TRANSIT_AI_CELERY_BACKEND", raising=False)
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://custom:6379/5")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://custom:6379/6")

    assert cc.broker_url() == "redis://custom:6379/5"
    assert cc.backend_url() == "redis://custom:6379/6"

    monkeypatch.setenv("TRANSIT_AI_CELERY_BROKER", "redis://docker:6379/1")
    monkeypatch.setenv("TRANSIT_AI_CELERY_BACKEND", "redis://docker:6379/2")
    assert cc.broker_url() == "redis://docker:6379/1"
    assert cc.backend_url() == "redis://docker:6379/2"


def test_defaults_when_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "TRANSIT_AI_CELERY_BROKER",
        "TRANSIT_AI_CELERY_BACKEND",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
    ):
        monkeypatch.delenv(key, raising=False)
    assert cc.broker_url() == cc.DEFAULT_BROKER
    assert cc.backend_url() == cc.DEFAULT_BACKEND


# ─────────────────────────── send / wait ───────────────────────────


def test_send_uses_task_name_and_passes_kwargs() -> None:
    client = _FakeCelery()

    handle = cc.send("predict_window", client=client, model_id="xgboost_v11_traffic")

    assert handle.task_name == "ml_pipeline.predict_window"
    assert handle.task_id == "fake-1"
    assert client.sent == [
        ("ml_pipeline.predict_window", {"model_id": "xgboost_v11_traffic"}),
    ]


def test_send_without_kwargs_passes_none() -> None:
    client = _FakeCelery()

    cc.send("train_xgboost", client=client)

    assert client.sent == [("ml_pipeline.train_xgboost", None)]


def test_send_unknown_key_raises_before_broker_call() -> None:
    client = _FakeCelery()
    with pytest.raises(KeyError):
        cc.send("unknown_task", client=client)
    assert client.sent == []


def test_wait_returns_result_on_success() -> None:
    client = _FakeCelery(states=["PENDING", "STARTED", "SUCCESS"], result={"status": "ok"})
    handle = cc.TaskHandle(task_id="fake-1", task_name="ml_pipeline.train_xgboost", key="train")

    out = cc.wait(handle, timeout=5, poll_interval=0, client=client)

    assert out == {"task_id": "fake-1", "state": "SUCCESS", "result": {"status": "ok"}}


def test_wait_returns_failure_state_without_result() -> None:
    client = _FakeCelery(states=["FAILURE"], result=RuntimeError("boom"))
    handle = cc.TaskHandle(task_id="fake-2", task_name="ml_pipeline.train_xgboost", key="train")

    out = cc.wait(handle, timeout=5, poll_interval=0, client=client)

    assert out["state"] == "FAILURE"
    assert out["result"] is None


def test_wait_times_out_instead_of_hanging() -> None:
    client = _FakeCelery(states=["PENDING"])
    handle = cc.TaskHandle(task_id="fake-3", task_name="ml_pipeline.train_xgboost", key="train")

    out = cc.wait(handle, timeout=0, poll_interval=0, client=client)

    assert out == {"task_id": "fake-3", "state": "TIMEOUT", "result": None}
