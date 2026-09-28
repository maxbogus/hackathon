"""Tests for Airflow DAG structure (transit_pipeline) — T-235.

Два контура:

A. Герметичный (без `import airflow`, только AST) — работает в `make mlops-test`:
   1. DAG-файл существует
   2. `dag_id="transit_pipeline"` и `schedule=None` (manual trigger only)
   3. Ровно 5 `@task`: harvest, train, mlflow_ingest, predict, leaderboard
   4. Цепочка зависимостей harvest → train → mlflow_ingest → predict → leaderboard
   5. Все стадии идут через `_run_celery` (задачи по имени), не через subprocess/uv
   6. В DAG нет импортов кода проекта (`app.*`, `transit_ai.*`) — инвариант
      переносимости: тот же DAG работает и в проектном Airflow, и в общем

B. С реальным Airflow (скипается без `apache-airflow`) — `make airflow-test`:
   7. DAG импортируется, dag_id/tasks корректны, downstream-цепочка верна

Запуск: make mlops-test (контур A) / make airflow-test (A + B).
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DAG_PATH = REPO_ROOT / "mlops" / "dags" / "transit_pipeline.py"
DAG_ID = "transit_pipeline"

EXPECTED_TASKS = {"harvest", "train", "mlflow_ingest", "predict", "leaderboard"}
EXPECTED_CHAIN = "harvest() >> train() >> mlflow_ingest() >> predict() >> leaderboard()"
FORBIDDEN_IMPORT_PREFIXES = ("app", "transit_ai", "ml.")


def _parse_dag() -> ast.Module:
    """Распарсить DAG-файл (без импорта apache-airflow)."""
    assert DAG_PATH.is_file(), f"DAG file missing: {DAG_PATH}"
    return ast.parse(DAG_PATH.read_text(encoding="utf-8"), filename=str(DAG_PATH))


def _decorator_name(node: ast.AST) -> str | None:
    """Имя декоратора: `@dag(...)` → 'dag', `@task` → 'task'."""
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorated_functions(tree: ast.Module, decorator: str) -> list[ast.FunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(_decorator_name(d) == decorator for d in node.decorator_list)
    ]


def _dag_keywords(tree: ast.Module) -> dict[str, ast.expr]:
    """Ключевые аргументы декоратора @dag (dag_id, schedule, tags, ...)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if _decorator_name(dec) == "dag" and isinstance(dec, ast.Call):
                return {kw.arg: kw.value for kw in dec.keywords if kw.arg}
    return {}


def test_dag_file_exists() -> None:
    assert DAG_PATH.is_file(), f"DAG file missing: {DAG_PATH}"


def test_dag_declares_dag_id_and_manual_schedule() -> None:
    """dag_id задан, schedule=None (никакого scheduler-расписания)."""
    kwargs = _dag_keywords(_parse_dag())
    assert kwargs, "декоратор @dag(...) не найден"
    dag_id = kwargs.get("dag_id")
    assert isinstance(dag_id, ast.Constant) and dag_id.value == DAG_ID
    schedule = kwargs.get("schedule")
    assert isinstance(schedule, ast.Constant) and schedule.value is None, (
        "DAG должен быть manual-only: schedule=None"
    )


def test_dag_has_exactly_expected_tasks() -> None:
    """Ровно 5 @task-функций с ожидаемыми именами (старый side-car удалён)."""
    task_names = {fn.name for fn in _decorated_functions(_parse_dag(), "task")}
    assert task_names == EXPECTED_TASKS, f"unexpected tasks: {task_names}"


def test_dag_dependencies_sequential_in_source() -> None:
    """Зависимости выражены явной цепочкой из 5 стадий."""
    source = DAG_PATH.read_text(encoding="utf-8")
    assert EXPECTED_CHAIN in source, f"не найдена цепочка зависимостей: {EXPECTED_CHAIN}"


def test_tasks_use_celery_client_not_subprocess() -> None:
    """Стадии — Celery-задачи по имени (в Airflow-контейнере uv/subprocess недоступны, F-133).

    Проверяем по AST: `subprocess` не импортируется, каждая стадия вызывает `_run_celery`.
    """
    tree = _parse_dag()
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert "subprocess" not in imported, f"DAG не должен импортировать subprocess: {imported}"

    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert calls.count("_run_celery") + calls.count("_default_submission_id") >= 1
    assert calls.count("_run_celery") >= len(EXPECTED_TASKS), f"_run_celery calls: {calls}"
    assert calls.count("_default_submission_id") == 1


def test_dag_does_not_import_project_code() -> None:
    """Инвариант переносимости: DAG не импортирует app.*/transit_ai.* (ни ML, ни backend)."""
    tree = _parse_dag()
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    offenders = [
        mod
        for mod in imported
        if any(mod == p or mod.startswith(f"{p}.") for p in FORBIDDEN_IMPORT_PREFIXES)
    ]
    assert not offenders, f"DAG импортирует код проекта: {offenders}"


# ─────────────────────────── Контур B: реальный Airflow ───────────────────────


def _load_dag_in_process():
    """Импортировать DAG-модуль (требует установленный apache-airflow)."""
    dags_dir = str(DAG_PATH.parent)
    if dags_dir not in sys.path:
        sys.path.insert(0, dags_dir)
    spec = importlib.util.spec_from_file_location(DAG_ID, DAG_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transit_pipeline_dag


@pytest.mark.slow
def test_dag_imports_with_airflow_and_dependencies_are_sequential() -> None:
    """DAG импортируется в Airflow и содержит верную downstream-цепочку."""
    pytest.importorskip("airflow", reason="apache-airflow эфемерен: make airflow-test")

    dag = _load_dag_in_process()
    assert dag.dag_id == DAG_ID

    tasks = {t.task_id: t for t in dag.tasks}
    assert set(tasks) == EXPECTED_TASKS

    def downstream(task_id: str) -> list[str]:
        return sorted(d.task_id for d in tasks[task_id].downstream_list)

    assert downstream("harvest") == ["train"]
    assert downstream("train") == ["mlflow_ingest"]
    assert downstream("mlflow_ingest") == ["predict"]
    assert downstream("predict") == ["leaderboard"]
    assert downstream("leaderboard") == []
