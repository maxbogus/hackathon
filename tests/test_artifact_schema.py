"""RED→GREEN test: docs/schemas/prediction_artifact.schema.json is loadable + accepts the example.

Contract-first: the schema is the single source of truth for what an ML artifact
meta.json may look like. Both `apps/backend/forecast/loader.py` (consumer) and
`ml/transit_ai/training/registry.py` (producer) import/validate against it.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "prediction_artifact.schema.json"
EXAMPLE_PATH = REPO_ROOT / "docs" / "schemas" / "prediction_artifact.example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    assert SCHEMA_PATH.exists(), f"Schema file missing: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def example() -> dict:
    assert EXAMPLE_PATH.exists(), f"Example file missing: {EXAMPLE_PATH}"
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_schema_file_is_valid_json_schema(schema: dict) -> None:
    """The schema itself must declare Draft-07 meta-schema fields."""
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema
    assert "model_id" in schema["required"]
    assert "files" in schema["required"]


def test_example_matches_schema(schema: dict, example: dict) -> None:
    """The hand-written example must validate without errors."""
    jsonschema.validate(instance=example, schema=schema)


def test_example_has_required_fields(example: dict) -> None:
    """Smoke test on the example: it must include the minimal ML artifact fields."""
    assert example["model_id"] == "baseline_v1"
    assert example["kind"] in {"baseline", "xgboost", "gru", "hybrid", "montecarlo"}
    assert "metrics" in example  # may be empty for dev artifacts


def test_schema_rejects_missing_model_id(schema: dict) -> None:
    """An artifact without model_id must be rejected (model_id is required)."""
    bad: dict = {"kind": "baseline", "version": "v0.1.0", "trained_at": "2026-01-01T00:00:00Z", "metrics": {"rmsle": 0.5}, "files": {"model": "model.pkl"}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)


def test_schema_rejects_invalid_kind(schema: dict) -> None:
    """kind must be one of the enumerated families (no typos)."""
    bad: dict = {"model_id": "x_v1", "kind": "deepseek", "version": "v0.1.0", "trained_at": "2026-01-01T00:00:00Z", "metrics": {"rmsle": 0.5}, "files": {"model": "model.pkl"}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)


def test_schema_rejects_negative_rmsle(schema: dict) -> None:
    """rmsle >= 0 (RMSE on log-scale)."""
    bad: dict = {"model_id": "x_v1", "kind": "baseline", "version": "v0.1.0", "trained_at": "2026-01-01T00:00:00Z", "metrics": {"rmsle": -0.1}, "files": {"model": "model.pkl"}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)
