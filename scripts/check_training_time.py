"""Check cumulative ML training time per R6 hackathon-rules (<= 60 min).

Usage:
    uv run python scripts/check_training_time.py
    uv run python scripts/check_training_time.py --limit-sec 3600
    uv run python scripts/check_training_time.py --artifacts-dir ml/artifacts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

R6_LIMIT_SEC = 3600.0  # 60 min


ArtifactRecord = dict[str, str | float]


def scan_artifacts(artifacts_dir: Path) -> list[ArtifactRecord]:
    """Scan meta.json in each model artifact directory."""
    records: list[ArtifactRecord] = []
    if not artifacts_dir.exists():
        return records
    for meta_path in sorted(artifacts_dir.glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError as e:
            print(f"WARNING: skipping {meta_path}: {e}", file=sys.stderr)
            continue
        model_id = meta.get("model_id", meta_path.parent.name)
        train_time = float(meta.get("train_time_sec", 0))
        records.append(
            {
                "model_id": model_id,
                "train_time_sec": train_time,
                "path": str(meta_path),
            }
        )
    return records


def check_total_time(
    records: list[ArtifactRecord],
    limit_sec: float = R6_LIMIT_SEC,
) -> tuple[bool, float, list[str]]:
    """Return (pass, total_sec, violations)."""
    total = sum(float(r["train_time_sec"]) for r in records)
    violations: list[str] = []
    if total > limit_sec:
        violations.append(
            f"Total training time {total:.0f}s ({total / 60:.1f}m) > "
            f"{limit_sec:.0f}s ({limit_sec / 60:.1f}m) -- R6 breach"
        )
    return (len(violations) == 0, total, violations)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check R6 training time limit")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("ml/artifacts"))
    parser.add_argument(
        "--limit-sec",
        type=float,
        default=R6_LIMIT_SEC,
        help=f"R6 training time limit (default: {R6_LIMIT_SEC}s = 60m)",
    )
    args = parser.parse_args()

    print(f"Scanning {args.artifacts_dir} for training time...")
    records = scan_artifacts(args.artifacts_dir)
    if not records:
        print("No artifacts found. Skipping R6 check.")
        return 0

    print(f"\n{'Model ID':<30} {'Time (sec)':>12} {'Time (min)':>12}")
    print("-" * 60)
    cumulative = 0.0
    for r in records:
        train_t = float(r["train_time_sec"])
        cumulative += train_t
        print(f"{r['model_id']:<30} {train_t:>12.1f} {train_t / 60:>12.2f}")
    print("-" * 60)
    print(f"{'TOTAL':<30} {cumulative:>12.1f} {cumulative / 60:>12.2f}")

    passed, total, violations = check_total_time(records, args.limit_sec)
    if passed:
        print(f"\nR6 PASS: training time {total / 60:.1f}m <= {args.limit_sec / 60:.1f}m")
        return 0
    for v in violations:
        print(f"\n{v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
