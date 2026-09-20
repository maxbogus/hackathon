"""ML artifact loader.

Reads model artifacts from the on-disk registry (one directory per model_id)
and validates their `meta.json` against `docs/schemas/prediction_artifact.schema.json`.

Architecture: см. `.clinerules/10-ml-as-scripts.md` (артефакты на диске,
переключение через `active.json`) и `.clinerules/08-contracts-and-artifacts.md`
(JSON Schema как контракт).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

# Repo root = apps/backend/app/forecast/loader.py → 4 levels up
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "prediction_artifact.schema.json"
ACTIVE_FILE = "active.json"


class ArtifactError(Exception):
    """Base for all artifact-loading errors."""


class ArtifactNotFoundError(ArtifactError):
    """meta.json or active.json missing on disk."""


class ArtifactValidationError(ArtifactError):
    """meta.json is present but does not validate against the schema."""


class ActiveArtifactNotFoundError(ArtifactError):
    """active.json pointer file is missing entirely."""


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    """In-memory representation of a validated ML artifact."""

    model_id: str
    kind: str
    version: str
    trained_at: str
    metrics: dict[str, float]
    files: dict[str, str]
    path: Path
    horizons: tuple[str, ...] = field(default_factory=tuple)
    granularities: tuple[str, ...] = field(default_factory=tuple)
    git_commit: str | None = None
    train_data_hash: str | None = None
    seed: int | None = None
    calibration: dict[str, Any] | None = None


class ArtifactLoader:
    """Loads and validates ML artifacts from a directory tree."""

    def __init__(
        self,
        artifacts_dir: Path | str = DEFAULT_ARTIFACTS_DIR,
        schema_path: Path | str = SCHEMA_PATH,
    ) -> None:
        self.artifacts_dir = Path(artifacts_dir)
        self.schema_path = Path(schema_path)
        self._schema: dict[str, Any] | None = None

    @property
    def schema(self) -> dict[str, Any]:
        """Lazy-load + cache the JSON Schema."""
        if self._schema is None:
            self._schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        return self._schema

    def _meta_path(self, model_id: str) -> Path:
        return self.artifacts_dir / model_id / "meta.json"

    def load(self, model_id: str) -> ModelArtifact:
        """Load + validate a specific artifact by its ID."""
        meta_path = self._meta_path(model_id)
        if not meta_path.is_file():
            available = (
                sorted(p.name for p in self.artifacts_dir.iterdir() if p.is_dir())
                if self.artifacts_dir.is_dir()
                else "no artifacts dir"
            )
            raise ArtifactNotFoundError(
                f"Artifact meta.json not found: {meta_path}. Available: {available}"
            )

        try:
            meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ArtifactValidationError(
                f"Artifact {model_id!r}: meta.json is not valid JSON: {exc}"
            ) from exc

        try:
            jsonschema.validate(instance=meta, schema=self.schema)
        except jsonschema.ValidationError as exc:
            raise ArtifactValidationError(
                f"Artifact {model_id!r}: meta.json does not validate against "
                f"{self.schema_path.name}: {exc.message}"
            ) from exc

        return ModelArtifact(
            model_id=meta["model_id"],
            kind=meta["kind"],
            version=meta["version"],
            trained_at=meta["trained_at"],
            metrics=dict(meta.get("metrics", {})),
            files=dict(meta.get("files", {})),
            path=meta_path.parent,
            horizons=tuple(meta.get("horizons", ())),
            granularities=tuple(meta.get("granularities", ())),
            git_commit=meta.get("git_commit"),
            train_data_hash=meta.get("train_data_hash"),
            seed=meta.get("seed"),
            calibration=meta.get("calibration"),
        )

    def get_active(self) -> ModelArtifact:
        """Load the artifact currently pointed to by `active.json`."""
        active_path = self.artifacts_dir / ACTIVE_FILE
        if not active_path.is_file():
            raise ActiveArtifactNotFoundError(
                f"No active model: {active_path} not found. "
                f"Train a model (make train-baseline) and activate it."
            )

        try:
            active: dict[str, Any] = json.loads(active_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ActiveArtifactNotFoundError(
                f"{active_path} is not valid JSON: {exc}"
            ) from exc

        model_id = active.get("model_id")
        if not model_id:
            raise ActiveArtifactNotFoundError(
                f"{active_path} must contain a 'model_id' field, got: {active}"
            )

        return self.load(model_id)


_loader_singleton: ArtifactLoader | None = None


def get_loader() -> ArtifactLoader:
    """FastAPI dependency: returns a singleton ArtifactLoader."""
    global _loader_singleton
    if _loader_singleton is None:
        _loader_singleton = ArtifactLoader()
    return _loader_singleton


def reset_loader_cache() -> None:
    """Test helper: clear the singleton (e.g. after monkeypatching env vars)."""
    global _loader_singleton
    _loader_singleton = None


__all__ = [
    "ActiveArtifactNotFoundError",
    "ArtifactError",
    "ArtifactLoader",
    "ArtifactNotFoundError",
    "ArtifactValidationError",
    "ModelArtifact",
    "get_loader",
    "reset_loader_cache",
]
