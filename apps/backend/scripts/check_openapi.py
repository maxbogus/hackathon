"""Verify that docs/api/openapi.json matches the live FastAPI app.

Invoked by `make api-check` (root Makefile) — CI gate against OpenAPI drift.

Usage:
    cd apps/backend && uv run python scripts/check_openapi.py
    # OR from root:
    make api-check

Exit codes:
    0 - openapi.json matches the live app (or is regenerated cleanly).
    1 - Drift detected (caller must regenerate via `make api-gen`).
    2 - Import error / missing file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = REPO_ROOT / "docs" / "api" / "openapi.json"


def main() -> int:
    if not OPENAPI_PATH.is_file():
        print(f"❌ Missing {OPENAPI_PATH}. Run `make api-gen` first.", file=sys.stderr)
        return 2

    try:
        from app.main import app
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}", file=sys.stderr)
        return 2

    live = app.openapi()
    on_disk = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))

    # Strip noisy defaults that FastAPI generates each call but don't affect schema semantically.
    # (e.g. operationId, security). We compare only what consumers see: paths + components.
    def _trim(schema: dict) -> dict:
        return {"paths": schema.get("paths", {}), "components": schema.get("components", {})}

    if _trim(live) == _trim(on_disk):
        print(f"✅ OpenAPI in sync with backend code ({len(live.get('paths', {}))} paths)")
        return 0

    print("❌ OpenAPI drift detected: docs/api/openapi.json is stale.")
    print("   Run `make api-gen` to regenerate.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
