"""Опциональный MLflow tracking для ML-скриптов (clinerule 10: ML вне Docker).

Принципы
--------
1. MLflow — **observability-слой, НЕ источник истины**. Источники истины остаются:
   `docs/schemas/prediction_artifact.schema.json`, `ml/artifacts/<id>/meta.json`,
   `predictions/*.json` (manifest), Postgres `predictions.is_active/is_etalon`.
2. **Мягкая деградация**: если mlflow не importable ИЛИ `TRANSIT_AI_MLFLOW=0|false|off|no`,
   все вызовы — no-op. ML-скрипты работают как раньше (ни одной записи на диск).
3. **Ничего в uv.lock**: mlflow ставится эфемерно —
   `uv run --with "mlflow>=2.16" python ...` (см. `make mlflow-run` / `make mlflow-demo`).

Переменные окружения
--------------------
TRANSIT_AI_MLFLOW            1/0 (по умолчанию: включено, если mlflow importable)
TRANSIT_AI_MLFLOW_EXPERIMENT default "transit-ai" (fallback: MLFLOW_EXPERIMENT_NAME)
MLFLOW_TRACKING_URI          default "sqlite:///<repo_root>/mlruns.db"
TRANSIT_AI_MLFLOW_ARTIFACTS  default "file:<repo_root>/mlartifacts"

Про file-store (проверено на MLflow 3.16):
    Файловый backend переведён в maintenance mode и по умолчанию **кидает исключение**
    ("The filesystem tracking backend ... is in maintenance mode", F-112).
    Поэтому дефолт — SQLite. Если всё же нужен `file:`-uri (совместимость со старыми
    прогонами) — трекер сам выставит `MLFLOW_ALLOW_FILE_STORE=true` (opt-out доступен).

Usage
-----
    from transit_ai.tracking import track_run

    with track_run("train-xgboost", params={"n_estimators": 200}) as run:
        run.log_metrics({"wape_score": 0.87})
        run.log_folds([0.2, 0.3], metric="rmsle")
        run.log_json(meta, "meta.json")
        print(run.summary_line())
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import types

REPO_ROOT = (
    Path(__file__).resolve().parents[3]
)  # ml/transit_ai/tracking/x.py → repo root
DEFAULT_TRACKING_URI = f"sqlite:///{REPO_ROOT / 'mlruns.db'}"
DEFAULT_ARTIFACT_ROOT = f"file:{REPO_ROOT / 'mlartifacts'}"
DEFAULT_EXPERIMENT = "transit-ai"
_OFF_VALUES = frozenset({"0", "false", "no", "off"})
_LEGACY_FILE_STORE_OPT_IN = "MLFLOW_ALLOW_FILE_STORE"


def _mlflow_handle() -> types.ModuleType | None:
    """Импортировать mlflow; None если не установлен (без кэша — тесты подменяют sys.modules)."""
    try:
        import mlflow
    except Exception:  # ImportError | RuntimeError (несовместимая версия)
        return None
    return mlflow


def is_enabled() -> bool:
    """Tracking включён? (env-флаг не выключает И mlflow importable)."""
    raw = os.environ.get("TRANSIT_AI_MLFLOW")
    if raw is not None and raw.strip().lower() in _OFF_VALUES:
        return False
    return _mlflow_handle() is not None


def tracking_uri() -> str:
    """URI хранилища ранов: MLFLOW_TRACKING_URI или локальная SQLite-БД в repo."""
    return os.environ.get("MLFLOW_TRACKING_URI") or DEFAULT_TRACKING_URI


def artifact_root() -> str:
    """Куда складывать артефакты ранов (model.pkl, meta.json)."""
    return os.environ.get("TRANSIT_AI_MLFLOW_ARTIFACTS") or DEFAULT_ARTIFACT_ROOT


def experiment_name() -> str:
    """Имя эксперимента (группа ранов)."""
    return (
        os.environ.get("TRANSIT_AI_MLFLOW_EXPERIMENT")
        or os.environ.get("MLFLOW_EXPERIMENT_NAME")
        or DEFAULT_EXPERIMENT
    )


def _stringify(value: object) -> str:
    """mlflow.log_params принимает только str — dict/list сериализуем в JSON (стабильно)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _as_float(value: object) -> float | None:
    """Привести к float для метрики; None для нечисловых значений (mlflow не примет bool)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _git_commit_short() -> str:
    """Короткий sha HEAD (best-effort; дёшево, поэтому без кэша)."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return "unknown"


def _ensure_experiment(handle: types.ModuleType, name: str) -> None:
    """Создать эксперимент с АБСОЛЮТНЫМ artifact_location, если его ещё нет.

    Без явного artifact_location DB-backed store пишет артефакты в ./mlruns/<id>
    относительно CWD — артефакты разъезжались бы между запусками из разных директорий.
    artifact_location неизменяем после создания, поэтому создаём эксперимент сами,
    а `mlflow.set_experiment(name)` ниже находит его по имени (не подменяя id вместо имени!).
    """
    client = handle.MlflowClient()
    if client.get_experiment_by_name(name) is None:
        client.create_experiment(name=name, artifact_location=artifact_root())


def _apply_legacy_file_store_opt_in(uri: str) -> None:
    """MLflow 3 держит file-store в maintenance mode (F-112).

    Если пользователь явно выбрал `file:`-uri — не перезатирая его выбор, включаем
    legacy-режим (`MLFLOW_ALLOW_FILE_STORE=true`), иначе первый же ран упадёт.
    """
    if uri.startswith("file:"):
        os.environ.setdefault(_LEGACY_FILE_STORE_OPT_IN, "true")


@dataclass
class RunTracker:
    """Обёртка над активным MLflow-раном. `enabled=False` → все методы no-op."""

    run_id: str | None = None
    enabled: bool = False
    name: str = ""

    def log_params(self, params: Mapping[str, object]) -> None:
        """Параметры прогона (не-скаляры → JSON-строка)."""
        handle = _mlflow_handle() if self.enabled and params else None
        if handle is None:
            return
        handle.log_params({str(k): _stringify(v) for k, v in params.items()})

    def log_metrics(
        self, metrics: Mapping[str, object], step: int | None = None
    ) -> None:
        """Числовые метрики; нечисловые значения тихо игнорируются."""
        handle = _mlflow_handle() if self.enabled and metrics else None
        if handle is None:
            return
        clean: dict[str, float] = {}
        for key, value in metrics.items():
            as_float = _as_float(value)
            if as_float is not None:
                clean[str(key)] = as_float
        if clean:
            handle.log_metrics(clean, step=step)

    def set_tags(self, tags: Mapping[str, object]) -> None:
        """Теги рана (provenance: git_commit, source, status)."""
        handle = _mlflow_handle() if self.enabled and tags else None
        if handle is None:
            return
        handle.set_tags({str(k): _stringify(v) for k, v in tags.items()})

    def log_artifact(self, path: str | Path) -> None:
        """Залогировать файл; несуществующий путь — тихо пропускаем."""
        handle = _mlflow_handle() if self.enabled else None
        target = Path(path)
        if handle is None or not target.exists():
            return
        handle.log_artifact(str(target))

    def log_json(
        self, payload: Mapping[str, object], filename: str = "meta.json"
    ) -> None:
        """Залогировать dict как JSON-артефакт (meta.json, отчёты, снапшоты)."""
        handle = _mlflow_handle() if self.enabled else None
        if handle is None:
            return
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / filename
            target.write_text(
                json.dumps(dict(payload), indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            handle.log_artifact(str(target))

    def log_folds(
        self,
        scores: Sequence[float],
        metric: str = "rmsle",
        fold_prefix: str = "fold",
    ) -> None:
        """Per-fold метрики: nested-ран на каждый fold + агрегаты на родителе."""
        handle = _mlflow_handle() if self.enabled and scores else None
        if handle is None:
            return
        values = [float(s) for s in scores]
        for idx, value in enumerate(values):
            with handle.start_run(nested=True, run_name=f"{fold_prefix}-{idx}"):
                handle.log_metric(metric, value, step=idx)
        self.log_metrics(
            {
                f"{fold_prefix}_mean_{metric}": statistics.fmean(values),
                f"{fold_prefix}_std_{metric}": statistics.pstdev(values),
                f"{fold_prefix}_n": float(len(values)),
            }
        )

    def summary_line(self) -> str:
        """Строка для консоли: видно, пишется ли ран и куда."""
        if self.enabled:
            return (
                f"MLflow: enabled (run_id={self.run_id}, uri={tracking_uri()}, "
                f"experiment={experiment_name()})"
            )
        return "MLflow: disabled (no-op) — включить: uv run --with mlflow …"


@contextmanager
def track_run(
    name: str,
    params: Mapping[str, object] | None = None,
    tags: Mapping[str, object] | None = None,
    nested: bool = False,
) -> Iterator[RunTracker]:
    """Открыть MLflow-ран (или no-op трекер, если tracking выключен/недоступен)."""
    handle = _mlflow_handle() if is_enabled() else None
    if handle is None:
        yield RunTracker(enabled=False, name=name)
        return

    uri = tracking_uri()
    _apply_legacy_file_store_opt_in(uri)
    handle.set_tracking_uri(uri)
    exp_name = experiment_name()
    _ensure_experiment(handle, exp_name)
    handle.set_experiment(exp_name)
    # F-113: run_name — пользовательский name, не имя эксперимента.
    # Раньше `name = experiment_name()` затирал аргумент, и все раны получали
    # одинаковый run_name = experiment_name, что ломало фильтрацию в mlflow_runs.
    run_name = name or exp_name

    with handle.start_run(run_name=run_name, nested=nested) as active:
        run = RunTracker(run_id=active.info.run_id, enabled=True, name=run_name)
        run.set_tags(
            {
                "transit_ai.tool": "transit-ai-ml",
                "transit_ai.git_commit": _git_commit_short(),
            }
        )
        if params:
            run.log_params(params)
        if tags:
            run.set_tags(tags)
        try:
            yield run
        except BaseException:
            # Помечаем ран упавшим, но не маскируем исходную ошибку.
            try:
                run.set_tags({"transit_ai.status": "failed"})
            except Exception:
                pass
            raise
        run.set_tags({"transit_ai.status": "finished"})
