"""Tests for transit_ai.tracking.mlflow_tracker.

Два режима (см. docs/MLFLOW.md):
  1. no-op — mlflow не установлен ИЛИ TRANSIT_AI_MLFLOW=0: ML-скрипты работают как раньше,
     ни одной записи на диск, ни одного исключения.
  2. tracking — mlflow importable + включено: ран (params/metrics/tags/per-fold
     вложенные раны) появляется в file-store.

Тесты режима 2 требуют mlflow (эфемерная установка):
    uv run --with "mlflow>=2.16" python -m pytest ml/tests/test_mlflow_tracker.py
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

from transit_ai.tracking import mlflow_tracker as tr

HAS_MLFLOW = importlib.util.find_spec("mlflow") is not None

ENV_KEYS = (
    "TRANSIT_AI_MLFLOW",
    "TRANSIT_AI_MLFLOW_EXPERIMENT",
    "TRANSIT_AI_MLFLOW_ARTIFACTS",
    "MLFLOW_TRACKING_URI",
    "MLFLOW_EXPERIMENT_NAME",
    "MLFLOW_ALLOW_FILE_STORE",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Изолировать тесты от env хоста (иначе результат зависит от машины)."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_disabled_env_writes_nothing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TRANSIT_AI_MLFLOW=0 → no-op: ничего на диск, ни одного исключения."""
    monkeypatch.setenv("TRANSIT_AI_MLFLOW", "0")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")

    assert tr.is_enabled() is False

    with tr.track_run("disabled-run", params={"a": 1}) as run:
        assert run.enabled is False
        assert run.run_id is None
        run.log_params({"b": 2})
        run.log_metrics({"wape_score": 0.5})
        run.log_folds([0.1, 0.2], metric="rmsle")
        run.set_tags({"k": "v"})
        run.log_artifact(tmp_path / "does-not-exist.txt")
        run.log_json({"x": 1})

    assert list(tmp_path.iterdir()) == []
    assert "disabled" in run.summary_line()


@pytest.mark.parametrize("off_value", ["0", "false", "FALSE", "off", "no", " False "])
def test_off_values_disable_tracking(
    monkeypatch: pytest.MonkeyPatch, off_value: str
) -> None:
    monkeypatch.setenv("TRANSIT_AI_MLFLOW", off_value)
    assert tr.is_enabled() is False


def test_noop_when_mlflow_not_importable(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mlflow не установлен → tracking молча выключается (graceful degradation)."""
    monkeypatch.setenv("TRANSIT_AI_MLFLOW", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")
    monkeypatch.setitem(sys.modules, "mlflow", None)  # `import mlflow` → ImportError

    assert tr.is_enabled() is False

    with tr.track_run("no-mlflow") as run:
        assert run.enabled is False
        run.log_metrics({"wape_score": 0.9})

    assert list(tmp_path.iterdir()) == []


def test_default_tracking_uri_is_sqlite_in_repo() -> None:
    """Дефолт — SQLite: file-store в MLflow 3 в maintenance mode (F-112)."""
    assert tr.DEFAULT_TRACKING_URI.startswith("sqlite:///")
    assert tr.DEFAULT_TRACKING_URI.endswith("mlruns.db")


def test_default_artifact_root_is_repo_mlartifacts() -> None:
    assert tr.DEFAULT_ARTIFACT_ROOT.startswith("file:")
    assert tr.DEFAULT_ARTIFACT_ROOT.endswith("mlartifacts")


def test_file_store_uri_enables_legacy_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """Явный `file:`-uri → включаем MLFLOW_ALLOW_FILE_STORE, не перезатирая выбор юзера."""
    monkeypatch.delenv("MLFLOW_ALLOW_FILE_STORE", raising=False)
    tr._apply_legacy_file_store_opt_in("file:/tmp/x/mlruns")
    assert os.environ["MLFLOW_ALLOW_FILE_STORE"] == "true"

    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "false")
    tr._apply_legacy_file_store_opt_in("file:/tmp/x/mlruns")
    assert os.environ["MLFLOW_ALLOW_FILE_STORE"] == "false"

    monkeypatch.delenv("MLFLOW_ALLOW_FILE_STORE", raising=False)
    tr._apply_legacy_file_store_opt_in("sqlite:///tmp/x.db")
    assert "MLFLOW_ALLOW_FILE_STORE" not in os.environ


def test_tracking_uri_env_override(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path}")
    assert tr.tracking_uri() == f"file:{tmp_path}"


def test_experiment_name_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    assert tr.experiment_name() == tr.DEFAULT_EXPERIMENT
    monkeypatch.setenv("TRANSIT_AI_MLFLOW_EXPERIMENT", "my-exp")
    assert tr.experiment_name() == "my-exp"


def test_stringify() -> None:
    """Не-скаляры (dict/list/None) → строки, иначе mlflow.log_params упадёт."""
    assert tr._stringify(None) == "None"
    assert tr._stringify(True) == "True"
    assert tr._stringify(42) == "42"
    assert tr._stringify(0.5) == "0.5"
    assert tr._stringify({"b": 1, "a": 2}) == '{"a": 2, "b": 1}'


@pytest.mark.skipif(not HAS_MLFLOW, reason='нужен mlflow: uv run --with "mlflow>=2.16"')
def test_enabled_writes_run_to_file_store(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Включённый tracking: params/metrics/tags + per-fold вложенные раны."""
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setenv("TRANSIT_AI_MLFLOW", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("TRANSIT_AI_MLFLOW_EXPERIMENT", "transit-ai-test")
    monkeypatch.setenv("TRANSIT_AI_MLFLOW_ARTIFACTS", f"file:{tmp_path / 'artifacts'}")

    with tr.track_run(
        "train-xgboost-test",
        params={"model_id": "xgboost_test", "seed": 42},
        tags={"transit_ai.source": "pytest"},
    ) as run:
        assert run.enabled is True
        assert run.run_id
        run.log_params({"n_estimators": 200, "hyperparams": {"max_depth": 6}})
        run.log_metrics({"wape_score": 0.83, "mae": 12.5})
        run.log_folds([0.20, 0.30], metric="rmsle")
        run.log_json({"model_id": "xgboost_test"}, "meta.json")

    assert "enabled" in run.summary_line()

    from mlflow.tracking import MlflowClient

    client = MlflowClient(tracking_uri=uri)
    data = client.get_run(run.run_id).data
    assert data.params["model_id"] == "xgboost_test"
    assert data.params["seed"] == "42"
    assert data.params["n_estimators"] == "200"
    assert data.params["hyperparams"] == '{"max_depth": 6}'
    assert data.metrics["wape_score"] == pytest.approx(0.83)
    assert data.metrics["fold_mean_rmsle"] == pytest.approx(0.25)
    assert data.tags["transit_ai.source"] == "pytest"
    assert data.tags["transit_ai.git_commit"]

    exp = client.get_experiment_by_name("transit-ai-test")
    assert exp is not None
    children = client.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{run.run_id}'",
    )
    assert len(children) == 2
    assert {c.data.metrics["rmsle"] for c in children} == {0.20, 0.30}

    artifact_paths = {a.path for a in client.list_artifacts(run.run_id)}
    assert "meta.json" in artifact_paths


@pytest.mark.skipif(not HAS_MLFLOW, reason='нужен mlflow: uv run --with "mlflow>=2.16"')
def test_run_name_is_user_provided(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """track_run(name=...) сохраняет name как run_name, не затирает experiment_name (F-113)."""
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setenv("TRANSIT_AI_MLFLOW", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("TRANSIT_AI_MLFLOW_EXPERIMENT", "exp-foo")
    monkeypatch.setenv("TRANSIT_AI_MLFLOW_ARTIFACTS", f"file:{tmp_path / 'artifacts'}")

    custom_name = "train-xgboost-my-version"
    with tr.track_run(custom_name, params={"model_id": "x"}) as run:
        assert run.enabled
        assert run.name == custom_name
        assert run.run_id

    from mlflow.tracking import MlflowClient

    client = MlflowClient(tracking_uri=uri)
    persisted = client.get_run(run.run_id)
    assert persisted.data.tags["mlflow.runName"] == custom_name
