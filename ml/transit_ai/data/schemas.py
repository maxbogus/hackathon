"""Parquet schema contract for predictions/*.parquet (T-033).

Single source of truth used by:
- ml/transit_ai/training/predict.py — writer
- apps/backend/forecast/loader.py — reader (will integrate in Phase 3)

Validates as a list of rows where each row matches `docs/schemas/predictions.schema.json`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PREDICTIONS_SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "predictions.schema.json"

# Per-column dtype map for pyarrow.
# Ints: stop_id, route_id nullable
# Floats: value, lower, upper
# Strings: timestamps ISO, horizon, granularity, model_id, scenario_id nullable
PREDICTIONS_ARROW_SCHEMA: dict[str, str] = {
    "period_start": "timestamp[ns]",
    "period_end": "timestamp[ns]",
    "stop_id": "int64",
    "route_id": "int64",  # nullable
    "value": "float64",
    "lower": "float64",
    "upper": "float64",
    "horizon": "string",
    "granularity": "string",
    "model_id": "string",
    "scenario_id": "string",  # nullable
}


def load_predictions_schema() -> dict[str, object]:
    """Load JSON Schema for predictions parquet."""
    import json

    raw: object = json.loads(PREDICTIONS_SCHEMA_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def validate_predictions_dataframe(df: Any) -> None:
    """Validate predictions DataFrame against JSON Schema. Raises jsonschema.ValidationError.

    Accepts pandas DataFrame (or any object with .copy()/.columns/.to_dict()).
    """
    import jsonschema

    schema = load_predictions_schema()
    # Convert timestamps → ISO strings for JSON Schema date-time format.
    # Duck-typed access to DataFrame columns — df is annotated as Any for flexibility.
    records = df.copy()
    for col in ("period_start", "period_end"):
        if col in records.columns:
            records[col] = (
                records[col].astype("datetime64[ns]").dt.strftime("%Y-%m-%dT%H:%M:%S")
            )
    jsonschema.validate(records.to_dict(orient="records"), schema)


__all__ = [
    "PREDICTIONS_ARROW_SCHEMA",
    "PREDICTIONS_SCHEMA_PATH",
    "load_predictions_schema",
    "validate_predictions_dataframe",
]
