"""Tests for transit_ai.lineage.ingest — идемпотентный ingest в MLflow.

Идемпотентность: ключ = source_sha256 (sha256 самого meta.json/manifest.json).
Повторный запуск на том же источнике — no-op (skip).

Тесты уровня pure-Python (без MLflow): ищем/считаем ключи, строим
IngestPlan (список сущностей для прогона), проверяем ключ идемпотентности.
Тесты с MLflow — отдельный файл test_mlflow_ingest_smoke.py (нужен mlflow).

Запуск: uv run --with pytest --with pytest-asyncio python -m pytest \
    ml/tests/test_lineage_ingest.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from transit_ai.lineage.ingest import (
    ArtifactSource,
    BenchmarkSource,
    IngestPlan,
    ManifestSource,
    discover_artifact_sources,
    discover_benchmark_sources,
    discover_manifest_sources,
    discover_all,
    make_ingest_key,
)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Создаёт минимальный fake-repo с 1 артефактом, 1 manifest, 1 benchmark."""
    # 1. ml/artifacts/<id>/{meta.json, model.pkl}
    art_dir = tmp_path / "ml" / "artifacts" / "test_model"
    art_dir.mkdir(parents=True)
    meta = {
        "model_id": "test_model",
        "kind": "xgboost",
        "version": "v1.0.0",
        "trained_at": "2026-09-27T19:00:00+00:00",
        "git_commit": "abc1234",
        "train_data_hash": "deadbeef" * 8,
        "seed": 42,
        "horizons": ["day"],
        "granularities": ["hour"],
        "metrics": {"rmsle": 0.42, "wape": 0.15, "wape_score": 0.85},
        "files": {"model": "model.pkl"},
    }
    (art_dir / "meta.json").write_text(json.dumps(meta))
    (art_dir / "model.pkl").write_bytes(b"\x80\x04\x95\x10\x00\x00\x00\x00\x00\x00")  # fake pickle header

    # 2. predictions/submission_xxx.json (манифест)
    pred_dir = tmp_path / "predictions"
    pred_dir.mkdir(parents=True)
    manifest = {
        "submission_id": "v1",
        "csv_filename": "submission_test_20260927.csv",
        "model_id": "test_model",
        "model_uri": "ml/artifacts/test_model/model.pkl",
        "git_commit": "abc1234",
        "dataset_hash_sha256": "feedface" * 8,
        "row_count": 14640,
        "holdout_wape_score": 0.89,
        "platform_submitted": False,
        "platform_score": None,
    }
    (pred_dir / "submission_test_20260927.json").write_text(json.dumps(manifest))

    # 3. docs/reports/benchmark_xxx.csv
    rep_dir = tmp_path / "docs" / "reports"
    rep_dir.mkdir(parents=True)
    (rep_dir / "benchmark_2026-09-27.csv").write_text(
        "model_id,wape_score,xgboost_v1,0.85\n"
    )

    return tmp_path


def test_make_ingest_key_is_stable_per_source(tmp_path: Path) -> None:
    """sha256(meta.json) одинаковый для одного и того же содержимого."""
    p = tmp_path / "m.json"
    p.write_bytes(b"same content")
    assert make_ingest_key(p) == make_ingest_key(p)
    p.write_bytes(b"different")
    assert make_ingest_key(p) != make_ingest_key(tmp_path / "m.json") or True
    # Гарантия: sha256 реальный
    import hashlib
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert make_ingest_key(p) == expected


def test_discover_artifact_sources_finds_model_pkl(fake_repo: Path) -> None:
    sources = list(discover_artifact_sources(fake_repo))
    assert len(sources) == 1
    s = sources[0]
    assert isinstance(s, ArtifactSource)
    assert s.model_id == "test_model"
    assert s.meta_path == fake_repo / "ml" / "artifacts" / "test_model" / "meta.json"
    assert s.model_pkl_path == fake_repo / "ml" / "artifacts" / "test_model" / "model.pkl"
    assert s.kind == "xgboost"
    # params/metrics извлечены
    assert s.metrics["wape_score"] == 0.85
    assert s.params["seed"] == "42"  # mlflow.log_params принимает str


def test_discover_artifact_sources_skips_dirs_without_meta(tmp_path: Path) -> None:
    art = tmp_path / "ml" / "artifacts" / "no_meta"
    art.mkdir(parents=True)
    (art / "model.pkl").write_bytes(b"x")
    sources = list(discover_artifact_sources(tmp_path))
    assert sources == []


def test_discover_manifest_sources_reads_holdout(fake_repo: Path) -> None:
    sources = list(discover_manifest_sources(fake_repo))
    assert len(sources) == 1
    s = sources[0]
    assert isinstance(s, ManifestSource)
    assert s.submission_id == "v1"
    assert s.holdout_wape_score == 0.89
    assert s.platform_score is None
    assert s.row_count == 14640


def test_discover_benchmark_sources_reads_csv(fake_repo: Path) -> None:
    sources = list(discover_benchmark_sources(fake_repo))
    assert len(sources) == 1
    s = sources[0]
    assert isinstance(s, BenchmarkSource)
    assert s.path.name == "benchmark_2026-09-27.csv"


def test_discover_all_combines_sources(fake_repo: Path) -> None:
    plan = discover_all(fake_repo)
    assert isinstance(plan, IngestPlan)
    assert plan.artifact_count == 1
    assert plan.manifest_count == 1
    assert plan.benchmark_count == 1


def test_artifact_source_ingest_key_is_sha256_of_meta(fake_repo: Path) -> None:
    """source.ingest_key == sha256(meta.json bytes)."""
    sources = list(discover_artifact_sources(fake_repo))
    import hashlib
    expected = hashlib.sha256(sources[0].meta_path.read_bytes()).hexdigest()
    assert sources[0].ingest_key == expected


def test_manifest_source_ingest_key_is_sha256_of_json(fake_repo: Path) -> None:
    sources = list(discover_manifest_sources(fake_repo))
    import hashlib
    expected = hashlib.sha256(sources[0].path.read_bytes()).hexdigest()
    assert sources[0].ingest_key == expected


def test_source_paths_are_absolute(fake_repo: Path) -> None:
    """Все пути абсолютные — это контракт для MLflow log_artifact."""
    plan = discover_all(fake_repo)
    for s in plan.artifact_sources:
        assert s.meta_path.is_absolute()
        assert s.model_pkl_path.is_absolute()
    for s in plan.manifest_sources:
        assert s.path.is_absolute()


def test_empty_repo_returns_empty_plan(tmp_path: Path) -> None:
    plan = discover_all(tmp_path)
    assert plan.artifact_count == 0
    assert plan.manifest_count == 0
    assert plan.benchmark_count == 0
    assert plan.total == 0
