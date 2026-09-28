"""Идемпотентный ingest существующих источников в MLflow.

Три типа источников:
  - ArtifactSource: ml/artifacts/<id>/meta.json + model.pkl
  - ManifestSource: predictions/<submission>.json
  - BenchmarkSource: docs/reports/benchmark_*.csv

discover_all(repo_root) → IngestPlan (списки sources).
Идемпотентность обеспечивается через source.ingest_key = sha256 самого файла.
MLflow-уровень проверки идемпотентности — в mlflow_ingest.py (по тегу
transit_ai.source_sha256 через mlflow.search_runs).

Этот модуль — pure stdlib (dataclass + hashlib), БЕЗ mlflow. Поэтому тесты
быстрые и без эфемерных зависимостей.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[3]


def make_ingest_key(path: Path) -> str:
    """sha256 файла в hex — стабильный ключ идемпотентности."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ArtifactSource:
    """Один ML-артефакт (ml/artifacts/<id>/meta.json + model.pkl)."""

    model_id: str
    meta_path: Path
    model_pkl_path: Path
    kind: str
    git_commit: str
    metrics: dict[str, float]
    params: dict[str, str]
    tags: dict[str, str]
    train_data_hash: str
    ingest_key: str  # = sha256(meta.json)

    @property
    def name(self) -> str:
        return f"artifact-{self.model_id}"


@dataclass(frozen=True)
class ManifestSource:
    """Манифест submission-а (predictions/<name>.json)."""

    path: Path
    submission_id: str
    model_id: str
    git_commit: str
    dataset_hash_sha256: str
    row_count: int
    holdout_wape_score: float | None
    platform_score: float | None
    platform_submitted: bool
    coefficients: dict[str, float]
    post_processing: list[str]
    train_date_range: list[str]
    submission_date_range: list[str]
    notes: str | None
    ingest_key: str

    @property
    def name(self) -> str:
        return f"manifest-{self.submission_id}"


@dataclass(frozen=True)
class BenchmarkSource:
    """benchmark CSV-отчёт (docs/reports/benchmark_*.csv)."""

    path: Path
    ingest_key: str

    @property
    def name(self) -> str:
        return f"benchmark-{self.path.stem}"


@dataclass(frozen=True)
class IngestPlan:
    """Результат discovery: что прогонять через MLflow."""

    artifact_sources: list[ArtifactSource] = field(default_factory=list)
    manifest_sources: list[ManifestSource] = field(default_factory=list)
    benchmark_sources: list[BenchmarkSource] = field(default_factory=list)

    @property
    def artifact_count(self) -> int:
        return len(self.artifact_sources)

    @property
    def manifest_count(self) -> int:
        return len(self.manifest_sources)

    @property
    def benchmark_count(self) -> int:
        return len(self.benchmark_sources)

    @property
    def total(self) -> int:
        return self.artifact_count + self.manifest_count + self.benchmark_count


def _stringify(value: object) -> str:
    """MLflow log_params принимает только str."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value), ensure_ascii=False, sort_keys=True, default=str)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _build_artifact_source(meta_path: Path, repo_root: Path) -> ArtifactSource:
    data = json.loads(meta_path.read_text())
    model_id = data["model_id"]
    kind = data.get("kind", "")
    git_commit = data.get("git_commit", "unknown")
    metrics_raw = data.get("metrics", {})
    metrics = {
        k: float(v) for k, v in metrics_raw.items() if isinstance(v, (int, float))
    }
    # params: всё из meta кроме metrics/files/train_data_hash → в params как JSON
    params: dict[str, str] = {}
    for k, v in data.items():
        if k in ("metrics", "files"):
            continue
        params[k] = _stringify(v)
    tags: dict[str, str] = {
        "transit_ai.source": "ml-artifact",
        "transit_ai.kind": kind,
        "transit_ai.git_commit": git_commit,
        "transit_ai.ingest_key": "",  # заполняется ниже
    }
    train_data_hash = data.get("train_data_hash", "")
    model_pkl_name = data.get("files", {}).get("model", "model.pkl")
    model_pkl_path = (meta_path.parent / model_pkl_name).resolve()
    ingest_key = make_ingest_key(meta_path)
    tags["transit_ai.ingest_key"] = ingest_key
    return ArtifactSource(
        model_id=model_id,
        meta_path=meta_path.resolve(),
        model_pkl_path=model_pkl_path,
        kind=kind,
        git_commit=git_commit,
        metrics=metrics,
        params=params,
        tags=tags,
        train_data_hash=train_data_hash,
        ingest_key=ingest_key,
    )


def discover_artifact_sources(
    repo_root: Path | str = REPO_ROOT_DEFAULT,
) -> list[ArtifactSource]:
    """Все артефакты в ml/artifacts/*/ с валидным meta.json + model.pkl."""
    root = Path(repo_root)
    artifacts_dir = root / "ml" / "artifacts"
    if not artifacts_dir.is_dir():
        return []
    sources: list[ArtifactSource] = []
    for meta_path in sorted(artifacts_dir.glob("*/meta.json")):
        if not meta_path.is_file():
            continue
        try:
            sources.append(_build_artifact_source(meta_path, root))
        except (json.JSONDecodeError, KeyError, ValueError):
            # Пропускаем битые meta.json — не падаем на одной ошибке.
            continue
    return sources


def discover_manifest_sources(
    repo_root: Path | str = REPO_ROOT_DEFAULT,
) -> list[ManifestSource]:
    """Все submission manifests в predictions/*.json (НЕ manifest от harvester)."""
    root = Path(repo_root)
    pred_dir = root / "predictions"
    if not pred_dir.is_dir():
        return []
    sources: list[ManifestSource] = []
    for path in sorted(pred_dir.glob("submission_*.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        # Обязательные поля
        if "submission_id" not in data:
            continue
        sources.append(
            ManifestSource(
                path=path.resolve(),
                submission_id=str(data.get("submission_id", "")),
                model_id=str(data.get("model_id", "")),
                git_commit=str(data.get("git_commit", "unknown")),
                dataset_hash_sha256=str(data.get("dataset_hash_sha256", "")),
                row_count=int(data.get("row_count", 0)),
                holdout_wape_score=(
                    float(data["holdout_wape_score"])
                    if isinstance(data.get("holdout_wape_score"), (int, float))
                    else None
                ),
                platform_score=(
                    float(data["platform_score"])
                    if isinstance(data.get("platform_score"), (int, float))
                    else None
                ),
                platform_submitted=bool(data.get("platform_submitted", False)),
                coefficients=dict(data.get("coefficients") or {}),
                post_processing=list(data.get("post_processing") or []),
                train_date_range=list(data.get("train_date_range") or []),
                submission_date_range=list(data.get("submission_date_range") or []),
                notes=str(data.get("notes")) if data.get("notes") else None,
                ingest_key=make_ingest_key(path),
            )
        )
    return sources


def discover_benchmark_sources(
    repo_root: Path | str = REPO_ROOT_DEFAULT,
) -> list[BenchmarkSource]:
    """Все benchmark CSV в docs/reports/benchmark_*.csv."""
    root = Path(repo_root)
    rep_dir = root / "docs" / "reports"
    if not rep_dir.is_dir():
        return []
    return [
        BenchmarkSource(path=p.resolve(), ingest_key=make_ingest_key(p))
        for p in sorted(rep_dir.glob("benchmark_*.csv"))
        if p.is_file()
    ]


def discover_all(repo_root: Path | str = REPO_ROOT_DEFAULT) -> IngestPlan:
    """Все источники разом."""
    return IngestPlan(
        artifact_sources=discover_artifact_sources(repo_root),
        manifest_sources=discover_manifest_sources(repo_root),
        benchmark_sources=discover_benchmark_sources(repo_root),
    )


_INGEST_KINDS = ("all", "artifacts", "manifests", "benchmarks")


def filter_plan(plan: IngestPlan, only: str = "all") -> IngestPlan:
    """Оставить в плане только выбранный вид источников (T-235).

    Args:
        plan: результат ``discover_all()``.
        only: ``all`` | ``artifacts`` | ``manifests`` | ``benchmarks``.

    Returns:
        Новый ``IngestPlan`` (dataclass frozen — мутация запрещена).

    Raises:
        ValueError: неизвестное значение ``only``.
    """
    if only not in _INGEST_KINDS:
        raise ValueError(f"only={only!r} не поддерживается; допустимо: {list(_INGEST_KINDS)}")
    if only == "all":
        return plan
    return IngestPlan(
        artifact_sources=plan.artifact_sources if only == "artifacts" else [],
        manifest_sources=plan.manifest_sources if only == "manifests" else [],
        benchmark_sources=plan.benchmark_sources if only == "benchmarks" else [],
    )


__all__ = [
    "REPO_ROOT_DEFAULT",
    "ArtifactSource",
    "BenchmarkSource",
    "IngestPlan",
    "ManifestSource",
    "discover_all",
    "discover_artifact_sources",
    "discover_benchmark_sources",
    "discover_manifest_sources",
    "filter_plan",
    "make_ingest_key",
]
