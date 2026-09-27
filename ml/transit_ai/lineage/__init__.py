"""Lineage-lite: streaming sha256 + snapshot manifest + ingest в MLflow.

Источник правды для train_data_hash в meta.json. Заменяет hash_dataframe
(training.registry.py), который pickle'ит DataFrame в RAM — на 8 GB train.csv
это OOM. Здесь — стриминг по 1 MB чанкам, O(1) по памяти.

См. clinerule 10 (ml-as-scripts) и .clinerules/24.
"""

from transit_ai.lineage.hashing import count_lines, streaming_sha256
from transit_ai.lineage.ingest import (
    ArtifactSource,
    BenchmarkSource,
    IngestPlan,
    ManifestSource,
    discover_all,
    discover_artifact_sources,
    discover_benchmark_sources,
    discover_manifest_sources,
    make_ingest_key,
)
from transit_ai.lineage.snapshot import Snapshot, capture, diff, read, write

__all__ = [
    "ArtifactSource",
    "BenchmarkSource",
    "IngestPlan",
    "ManifestSource",
    "Snapshot",
    "capture",
    "count_lines",
    "diff",
    "discover_all",
    "discover_artifact_sources",
    "discover_benchmark_sources",
    "discover_manifest_sources",
    "make_ingest_key",
    "read",
    "streaming_sha256",
    "write",
]
