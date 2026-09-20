"""Root conftest: ensures repository root is on sys.path and provides shared fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is importable (so 'apps.*', 'ml.*', 'tests.fixtures' resolve)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
