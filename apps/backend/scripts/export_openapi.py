"""Export FastAPI OpenAPI schema to docs/api/openapi.json.

Invoked by `make api-gen` (root Makefile).

Usage:
    cd apps/backend && uv run python scripts/export_openapi.py
    # OR from root:
    make api-gen

Exit codes:
    0 - OpenAPI exported successfully.
    1 - Failed (no app, import error, IO error).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # apps/backend/scripts → repo root
OUTPUT_PATH = REPO_ROOT / "docs" / "api" / "openapi.json"


def main() -> int:
    try:
        from app.main import app  # noqa: PLC0415 — lazy import for clearer error
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}", file=sys.stderr)
        print("Hint: run from apps/backend with `uv run python scripts/export_openapi.py`.", file=sys.stderr)
        return 1

    schema = app.openapi()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    paths = len(schema.get("paths", {}))
    print(f"✅ Exported OpenAPI ({paths} paths) → {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
