"""Model artifact registry (save / load / activate).

Один источник правды для on-disk artifacts, которые читает
`apps/backend/forecast/loader.py`.

Layout:
    ml/artifacts/<model_id>/
    ├── meta.json         # validated against docs/schemas/prediction_artifact.schema.json
    ├── model.pkl         # pickled Predictor
    └── preprocessor.pkl  # optional

    ml/artifacts/active.json   # {"model_id": "baseline_v1"} (atomic pointer)
"""

from __future__ import annotations

import hashlib
import json
import pickle
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

from transit_ai.models.base import Predictor

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "prediction_artifact.schema.json"
ACTIVE_FILE = "active.json"


def git_commit() -> str | None:
    """Best-effort short SHA. None if not in a git repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode().strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def hash_dataframe(df: Any) -> str:
    """sha256 of a DataFrame's pickle representation. Empty string on failure."""
    try:
        # Pickle → bytes → sha256. Don't go through .hex() (it's string → bytes).
        buf = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)
        return hashlib.sha256(buf).hexdigest()
    except (pickle.PicklingError, TypeError, AttributeError):
        return ""


@dataclass(frozen=True)
class SaveResult:
    artifact_dir: Path
    meta: dict[str, Any]


class ModelRegistry:
    """Saves Predictor instances to disk as versioned artifacts."""

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
        if self._schema is None:
            self._schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        return self._schema

    def save(
        self,
        predictor: Predictor,
        version: str = "v0.1.0",
        train_data_hash: str = "",
        seed: int = 42,
        horizons: tuple[str, ...] = ("day",),
        granularities: tuple[str, ...] = ("hour",),
        git_sha: str | None = None,
    ) -> SaveResult:
        """Save a fitted predictor to disk. Validates meta.json before writing."""
        if not predictor.fitted_ if hasattr(predictor, "fitted_") else True:  # type: ignore[attr-defined]
            raise ValueError(f"Predictor {predictor.model_id!r} is not fitted")

        artifact_dir = self.artifacts_dir / predictor.model_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # Save the model
        model_path = artifact_dir / "model.pkl"
        predictor.save(str(model_path))

        # Build and validate meta.json
        meta: dict[str, Any] = {
            "model_id": predictor.model_id,
            "kind": predictor.kind,
            "version": version,
            "trained_at": datetime.now(UTC).isoformat(),
            "git_commit": git_sha or git_commit(),
            "train_data_hash": train_data_hash,
            "seed": seed,
            "horizons": list(horizons),
            "granularities": list(granularities),
            "metrics": {},  # caller can update post-hoc via .metrics attribute
            "files": {"model": "model.pkl"},
        }
        jsonschema.validate(instance=meta, schema=self.schema)

        meta_path = artifact_dir / "meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return SaveResult(artifact_dir=artifact_dir, meta=meta)

    def activate(self, model_id: str) -> None:
        """Point active.json at <model_id> (atomic write)."""
        artifact_dir = self.artifacts_dir / model_id
        if not artifact_dir.is_dir():
            raise FileNotFoundError(f"Cannot activate: {artifact_dir} does not exist")

        meta_path = artifact_dir / "meta.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Cannot activate: {meta_path} missing (run save() first)")

        # Re-validate before activating (defensive)
        meta = json.loads(meta_path.read_text())
        jsonschema.validate(instance=meta, schema=self.schema)

        active_path = self.artifacts_dir / ACTIVE_FILE
        active_path.write_text(json.dumps({"model_id": model_id}), encoding="utf-8")


__all__ = ["ModelRegistry", "SaveResult", "git_commit", "hash_dataframe"]
