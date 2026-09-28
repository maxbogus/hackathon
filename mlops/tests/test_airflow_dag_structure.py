"""Tests for Airflow DAG structure (transit_side_car).

Два контура:

A. Герметичный (без `import airflow`, только AST) — работает в `make mlops-test`:
   1. DAG-файл существует
   2. `dag_id="transit_side_car"` и `schedule=None` (manual trigger only)
   3. Ровно 3 `@task`-функции: lineage_snapshot, mlflow_ingest, mlflow_leaderboard
   4. Цепочка зависимостей `snap >> ing >> lb`
   5. Таски идут через subprocess (`uv`), а не импортируют ML-код проекта
   6. В DAG нет импортов кода проекта (`app.*`, `transit_ai.*`) — инвариант
      переносимости: тот же DAG работает и на хосте, и в общем Airflow

B. С реальным Airflow (скипается без `apache-airflow`) — `make airflow-test`:
   7. DAG импортируется, dag_id/tasks корректны, downstream-цепочка верна

Запуск: make mlops-test (контур A) / make airflow-test (A + B).
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DAG_PATH = REPO_ROOT / "mlops" / "dags" / "transit_side_car.py"

EXPECTED_TASKS = {"lineage_snapshot", "mlflow_ingest", "mlflow_leaderboard"}
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
    assert isinstance(dag_id, ast.Constant) and dag_id.value == "transit_side_car"
    schedule = kwargs.get("schedule")
    assert isinstance(schedule, ast.Constant) and schedule.value is None, (
        "DAG должен быть manual-only: schedule=None"
    )


def test_dag_has_exactly_three_expected_tasks() -> None:
    """Ровно 3 @task-функции с ожидаемыми именами."""
    task_names = {fn.name for fn in _decorated_functions(_parse_dag(), "task")}
    assert task_names == EXPECTED_TASKS, f"unexpected tasks: {task_names}"


def test_dag_dependencies_sequential_in_source() -> None:
    """Зависимости выражены явной цепочкой snap >> ing >> lb."""
    source = DAG_PATH.read_text(encoding="utf-8")
    assert "snap >> ing >> lb" in source, "не найдена цепочка зависимостей snap >> ing >> lb"


def test_tasks_use_subprocess_not_pure_python() -> None:
    """Таски вызывают uv subprocess (не импортируют ML-код) — иначе загрязним venv."""
    source = DAG_PATH.read_text(encoding="utf-8")
    assert "_run_uv_subprocess" in source
    assert source.count("_run_uv_subprocess") >= 3


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
    spec = importlib.util.spec_from_file_location("transit_side_car", DAG_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transit_side_car_dag


@pytest.mark.slow
def test_dag_imports_with_airflow_and_dependencies_are_sequential() -> None:
    """DAG импортируется в Airflow и содержит верную downstream-цепочку."""
    pytest.importorskip("airflow", reason="apache-airflow эфемерен: make airflow-test")

    dag = _load_dag_in_process()
    assert dag.dag_id == "transit_side_car"

    tasks = {t.task_id: t for t in dag.tasks}
    assert set(tasks) == EXPECTED_TASKS

    snap_down = sorted(d.task_id for d in tasks["lineage_snapshot"].downstream_list)
    ing_down = sorted(d.task_id for d in tasks["mlflow_ingest"].downstream_list)
    lead_down = sorted(d.task_id for d in tasks["mlflow_leaderboard"].downstream_list)

    assert snap_down == ["mlflow_ingest"]
    assert ing_down == ["mlflow_leaderboard"]
    assert lead_down == []
