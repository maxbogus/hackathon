#!/usr/bin/env python3
"""Идемпотентный ingest существующих источников в MLflow.

Для каждого source проверяем, есть ли уже run с тегом transit_ai.ingest_key.
Если есть — skip. Иначе — создаём run с params/metrics/tags + log_artifact.

Sources:
  - ml/artifacts/*/meta.json + model.pkl  (23 артефакта)
  - predictions/*.json                    (53 манифеста)
  - docs/reports/benchmark_*.csv         (5 отчётов)

Идемпотентность: ключ = sha256(meta.json/manifest.csv). Повторный прогон — no-op.

Usage:
    make mlflow-ingest
    cd ml && uv run --with mlflow python scripts/mlflow_ingest.py
    cd ml && uv run --with mlflow python scripts/mlflow_ingest.py --only artifacts
    cd ml && uv run --with mlflow python scripts/mlflow_ingest.py --only manifests
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ml/
sys.path.insert(0, str(ROOT))

from transit_ai.lineage.ingest import (  # noqa: E402
    ArtifactSource,
    BenchmarkSource,
    ManifestSource,
    discover_all,
    filter_plan,
)
from transit_ai.tracking import (  # noqa: E402
    experiment_name,
    is_enabled,
    track_run,
    tracking_uri,
)


def _already_ingested(client, source, exp_id: str) -> bool:
    """Поиск ранов по тегу transit_ai.ingest_key в текущем эксперименте."""
    existing = client.search_runs(
        experiment_ids=[exp_id],
        filter_string=f"tags.transit_ai.ingest_key = '{source.ingest_key}'",
        max_results=1,
    )
    return len(existing) > 0


def ingest_artifact(client, source: ArtifactSource, exp_id: str) -> str:
    if _already_ingested(client, source, exp_id):
        return "skipped"
    run_name = f"artifact-{source.model_id}"
    with track_run(
        run_name,
        tags={
            "transit_ai.source": "ml-artifact",
            "transit_ai.kind": source.kind,
            "transit_ai.git_commit": source.git_commit,
            "transit_ai.ingest_key": source.ingest_key,
            "transit_ai.model_id": source.model_id,
        },
    ) as run:
        if not run.enabled:
            return "disabled"
        run.log_params(source.params)
        run.log_metrics(source.metrics)
        if source.model_pkl_path.is_file():
            run.log_artifact(source.model_pkl_path)
        run.log_artifact(source.meta_path)
        return "created"


def ingest_manifest(client, source: ManifestSource, exp_id: str) -> str:
    if _already_ingested(client, source, exp_id):
        return "skipped"
    run_name = f"submission-{source.submission_id}"
    with track_run(
        run_name,
        params={
            "submission_id": source.submission_id,
            "model_id": source.model_id,
            "git_commit": source.git_commit,
            "dataset_hash_sha256": source.dataset_hash_sha256,
            "row_count": source.row_count,
            "post_processing": ",".join(source.post_processing),
            "coefficients": ",".join(
                f"{k}={v}" for k, v in source.coefficients.items()
            ),
            "train_date_range": ",".join(source.train_date_range),
            "submission_date_range": ",".join(source.submission_date_range),
        },
        tags={
            "transit_ai.source": "submission-manifest",
            "transit_ai.ingest_key": source.ingest_key,
            "transit_ai.platform_submitted": str(source.platform_submitted),
        },
    ) as run:
        if not run.enabled:
            return "disabled"
        # Metrics: holdout + platform (если есть)
        if source.holdout_wape_score is not None:
            run.log_metrics({"holdout_wape_score": source.holdout_wape_score})
        if source.platform_score is not None:
            run.log_metrics({"platform_score": source.platform_score})
        # Drift = platform - holdout (если оба есть)
        if source.holdout_wape_score is not None and source.platform_score is not None:
            run.log_metrics(
                {"drift_wape_score": source.platform_score - source.holdout_wape_score}
            )
        run.log_artifact(source.path)
        if source.notes:
            run.log_json({"notes": source.notes}, "notes.json")
        return "created"


def ingest_benchmark(client, source: BenchmarkSource, exp_id: str) -> str:
    if _already_ingested(client, source, exp_id):
        return "skipped"
    run_name = source.name
    with track_run(
        run_name,
        tags={
            "transit_ai.source": "benchmark-csv",
            "transit_ai.ingest_key": source.ingest_key,
        },
    ) as run:
        if not run.enabled:
            return "disabled"
        # Парсим CSV: первая строка — header, далее data
        import csv

        with source.path.open() as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return "empty"
        run.log_params(
            {
                "n_rows": len(rows) - 1,
                "columns": ",".join(rows[0]),
            }
        )
        run.log_artifact(source.path)
        return "created"


def main() -> int:
    parser = argparse.ArgumentParser(description="Idempotent MLflow ingest")
    parser.add_argument(
        "--only",
        choices=["artifacts", "manifests", "benchmarks", "all"],
        default="all",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not is_enabled():
        print("MLflow выключен. Включить: uv run --with mlflow>=2.16 python ...")
        return 1

    import mlflow

    mlflow.set_tracking_uri(tracking_uri())
    exp_name = experiment_name()
    mlflow.set_experiment(exp_name)
    exp_id = mlflow.get_experiment_by_name(exp_name).experiment_id
    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri())

    plan = discover_all()
    plan = filter_plan(plan, args.only)

    if not args.quiet:
        print(f"experiment: {exp_name} (id={exp_id})")
        print(f"uri:        {tracking_uri()}")
        print(
            f"sources:    {plan.total} ({plan.artifact_count} artifacts + "
            f"{plan.manifest_count} manifests + {plan.benchmark_count} benchmarks)"
        )
        print()

    counts = {"created": 0, "skipped": 0, "disabled": 0, "empty": 0, "errors": 0}
    t0 = time.monotonic()

    for source in plan.artifact_sources:
        try:
            r = ingest_artifact(client, source, exp_id)
            counts[r] = counts.get(r, 0) + 1
            if not args.quiet:
                print(f"  artifact  {source.model_id:30} → {r}")
        except Exception as exc:
            counts["errors"] += 1
            if not args.quiet:
                print(f"  artifact  {source.model_id} → ERROR: {exc}")

    for source in plan.manifest_sources:
        try:
            r = ingest_manifest(client, source, exp_id)
            counts[r] = counts.get(r, 0) + 1
            if not args.quiet:
                print(f"  manifest  {source.submission_id[:35]:35} → {r}")
        except Exception as exc:
            counts["errors"] += 1
            if not args.quiet:
                print(f"  manifest  {source.submission_id} → ERROR: {exc}")

    for source in plan.benchmark_sources:
        try:
            r = ingest_benchmark(client, source, exp_id)
            counts[r] = counts.get(r, 0) + 1
            if not args.quiet:
                print(f"  benchmark {source.path.name:40} → {r}")
        except Exception as exc:
            counts["errors"] += 1
            if not args.quiet:
                print(f"  benchmark {source.path.name} → ERROR: {exc}")

    elapsed = time.monotonic() - t0
    if not args.quiet:
        print()
        print(
            f"created={counts['created']} skipped={counts['skipped']} "
            f"errors={counts['errors']} time={elapsed:.1f}s"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
