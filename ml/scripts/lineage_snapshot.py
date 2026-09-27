#!/usr/bin/env python3
"""Lineage snapshot: sha256+size+mtime+rows для файла данных → git-trackable JSON.

Использование:
    cd ml && uv run python scripts/lineage_snapshot.py \\
        --input ../data/real/train.csv \\
        --output ../docs/lineage/datasets/real_ridership.json

Или через Makefile:
    make lineage-snapshot INPUT=data/real/train.csv \\
        OUTPUT=docs/lineage/datasets/real_ridership.json

По умолчанию skip_header=True (CSV с заголовком → rows = data-rows).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ml/
sys.path.insert(0, str(ROOT))

from transit_ai.lineage.snapshot import capture, write  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture lineage snapshot for a data file")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="путь к файлу данных (например data/real/train.csv)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="куда писать snapshot JSON (например docs/lineage/datasets/real_ridership.json)",
    )
    parser.add_argument(
        "--no-skip-header",
        action="store_true",
        help="НЕ вычитать header из rows (rows = все строки включая header)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="не выводить progress",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input не найден: {args.input}", file=sys.stderr)
        return 1

    skip_header = not args.no_skip_header
    t0 = time.monotonic()
    if not args.quiet:
        print(f"snapshot: {args.input} ({args.input.stat().st_size:,} bytes)")
    snap = capture(args.input, skip_header=skip_header)
    elapsed = time.monotonic() - t0

    out = write(snap, args.output)
    if not args.quiet:
        print(f"sha256:   {snap.sha256}")
        print(f"rows:     {snap.rows:,}" + (" (data, без header)" if skip_header else ""))
        print(f"size:     {snap.size_bytes:,} bytes")
        print(f"captured: {snap.captured_at}")
        print(f"output:   {out} ({out.stat().st_size:,} bytes)")
        print(f"time:     {elapsed:.1f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
