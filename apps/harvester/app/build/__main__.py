"""`python -m app.build` → CLI external ETL (шаг 0, T-231)."""

from __future__ import annotations

import sys

from app.build.cli import main

if __name__ == "__main__":
    sys.exit(main())
