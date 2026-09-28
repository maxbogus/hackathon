"""Tests for ml_pipeline.run_ml_script allowlist-таска (T-235).

Проверяем, что оркестратор может запускать lineage/MLflow-шаги тем же
механизмом, что train/predict, но только из allowlist:
  - неизвестный скрипт → error с перечнем разрешённых (никакого subprocess)
  - известный → вызов uv с зафиксированными аргументами
  - mlflow-скрипты получают --with mlflow (эфемерная зависимость)
  - extra_args добавляются в конец
  - ненулевой код возврата → error со stderr
  - таск зарегистрирован в Celery-приложении
"""

from __future__ import annotations

from typing import Any

from app.celery_app import celery_app
from app.tasks import ML_SCRIPT_ALLOWLIST, _run_uv_with_packages, run_ml_script_task
import pytest


@pytest.fixture()
def captured(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Перехватить вызов uv-скрипта и записать аргументы."""
    calls: list[dict[str, Any]] = []

    def _fake(script: str, args: Any, packages: Any) -> tuple[int, str, str]:
        calls.append({"script": script, "args": list(args), "packages": list(packages)})
        return 0, "ok-output", ""

    monkeypatch.setattr("app.tasks._run_uv_with_packages", _fake)
    return calls


def test_task_is_registered() -> None:
    assert "ml_pipeline.run_ml_script" in set(celery_app.tasks.keys())


def test_allowlist_keys_are_stable() -> None:
    assert sorted(ML_SCRIPT_ALLOWLIST) == [
        "lineage_snapshot",
        "mlflow_ingest",
        "mlflow_leaderboard",
    ]


def test_unknown_script_returns_error_without_running_uv(
    captured: list[dict[str, Any]],
) -> None:
    result = run_ml_script_task(script="rm -rf /", extra_args=["--x"])

    assert result["status"] == "error"
    assert "allowlist" in result["error"]
    assert result["allowed"] == [
        "lineage_snapshot",
        "mlflow_ingest",
        "mlflow_leaderboard",
    ]
    assert captured == []


def test_lineage_snapshot_runs_with_fixed_args(
    captured: list[dict[str, Any]],
) -> None:
    result = run_ml_script_task(script="lineage_snapshot")

    assert result["status"] == "ok"
    assert captured[0]["script"] == "scripts/lineage_snapshot.py"
    args = captured[0]["args"]
    # Пути абсолютные (T-235): иначе при cwd=ml/ или cwd=apps/ml_pipeline они резолвятся по-разному
    assert args[0] == "--input" and args[1].endswith("data/real/train.csv")
    assert args[2] == "--output" and args[3].endswith("docs/lineage/datasets/real_ridership.json")
    assert captured[0]["packages"] == []
    assert result["stdout_tail"] == "ok-output"


def test_mlflow_scripts_use_ephemeral_package(
    captured: list[dict[str, Any]],
) -> None:
    run_ml_script_task(script="mlflow_ingest")

    assert captured[0]["script"] == "scripts/mlflow_ingest.py"
    assert captured[0]["packages"] == ["mlflow>=2.16"]


def test_mlflow_leaderboard_passes_top_argument(
    captured: list[dict[str, Any]],
) -> None:
    run_ml_script_task(script="mlflow_leaderboard")

    assert captured[0]["args"] == ["--top", "30"]


def test_extra_args_are_appended(captured: list[dict[str, Any]]) -> None:
    result = run_ml_script_task(script="mlflow_ingest", extra_args=["--only", "artifacts"])

    assert captured[0]["args"] == ["--only", "artifacts"]
    assert result["args"] == ["--only", "artifacts"]


def test_nonzero_returncode_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.tasks._run_uv_with_packages",
        lambda _script, _args, _packages: (1, "partial", "boom: traceback"),
    )

    result = run_ml_script_task(script="mlflow_ingest")

    assert result["status"] == "error"
    assert result["returncode"] == 1
    assert "boom" in result["stderr"]


def test_run_uv_with_packages_builds_uv_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяем сборку argv: uv --directory ml run [--with pkg] python script args."""
    seen: dict[str, Any] = {}

    class _Proc:
        returncode = 0
        stdout = "out"
        stderr = ""

    def _fake_run(cmd: list[str], **kwargs: Any) -> _Proc:
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return _Proc()

    monkeypatch.setattr("app.tasks.subprocess.run", _fake_run)

    rc, out, err = _run_uv_with_packages(
        "scripts/mlflow_ingest.py", ["--top", "5"], ["mlflow>=2.16"]
    )

    assert (rc, out, err) == (0, "out", "")
    assert seen["cmd"][:4] == ["uv", "--directory", seen["cmd"][2], "run"]
    assert seen["cmd"][2].endswith("/ml")
    assert seen["cmd"][4:6] == ["--with", "mlflow>=2.16"]
    assert seen["cmd"][6:] == ["python", "scripts/mlflow_ingest.py", "--top", "5"]
    # Регресс-гард: `--with` ДО `python`, иначе uv передал бы флаг скрипту
    assert seen["cmd"].index("--with") < seen["cmd"].index("python")
    assert seen["kwargs"]["check"] is False


def test_python_runner_skips_uv_and_with(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-235: в Docker (ML_PIPELINE_ML_RUNNER=python) запускаем системным python."""
    seen: dict[str, Any] = {}

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd: list[str], **kwargs: Any) -> _Proc:
        seen["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr("app.tasks.settings.ml_runner", "python")
    monkeypatch.setattr("app.tasks.subprocess.run", _fake_run)

    _run_uv_with_packages("scripts/mlflow_ingest.py", ["--top", "3"], ["mlflow>=2.16"])

    assert seen["cmd"] == ["python", "scripts/mlflow_ingest.py", "--top", "3"]
    assert "--with" not in seen["cmd"]
    assert "uv" not in seen["cmd"]
