#!/usr/bin/env python3
"""pyscn_compare.py — сравнить текущий pyscn report с baseline (CI gate).

Usage:
    uv run python scripts/pyscn_compare.py \\
        --baseline ai/analysis/pyscn-baseline.json \\
        --current .pyscn/report.json \\
        --max-delta-complexity 0.5 \\
        --max-delta-duplication 3.0 \\
        --max-delta-health -5.0

Exit code 0 — все метрики в пределах delta.
Exit code 1 — регресс (push блокируется).

Source: lawcopilot-api/.github/workflows/pyscn_compare.py (адаптация).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: str | Path) -> dict:
    """Load JSON. Handles both flat summary dict and full pyscn report."""
    with Path(path).open() as f:
        return json.load(f)


def extract_summary(report: dict) -> dict:
    """pyscn report → flat dict с метриками baseline.

    Если на входе уже flat (как baseline.json), возвращаем как есть.
    """
    if "summary" in report:
        s = report["summary"]
        return {
            "health_score": s.get("health_score", 0),
            "grade": s.get("grade", "?"),
            "complexity_avg": s.get("average_complexity", 0),
            "cognitive_complexity_avg": s.get("average_cognitive_complexity", 0),
            "duplication_pct": s.get("code_duplication_percentage", 0),
            "dead_code": s.get("dead_code_count", 0),
            "high_coupling": s.get("high_coupling_classes", 0),
            "high_complexity_count": s.get("high_complexity_count", 0),
            "arch_compliance": s.get("arch_compliance", 100),
        }
    return report


def compare(
    baseline: dict,
    current: dict,
    max_delta_complexity: float,
    max_delta_duplication: float,
    max_delta_health: float,
) -> int:
    """Print delta + return exit code."""
    b = baseline
    c = current

    print("PySCN Delta Report (vs baseline)")
    print("=" * 60)

    metrics = [
        ("health_score", "Health score", 0),
        ("complexity_avg", "Cyclomatic complexity avg", 1),
        ("cognitive_complexity_avg", "Cognitive complexity avg", 1),
        ("duplication_pct", "Duplication %", 1),
        ("dead_code", "Dead code", 0),
        ("high_coupling", "High coupling classes", 0),
        ("high_complexity_count", "High complexity functions", 0),
        ("arch_compliance", "Arch compliance", 0),
    ]

    errors: list[str] = []

    for key, label, decimals in metrics:
        b_val = b.get(key, 0)
        c_val = c.get(key, 0)
        delta = c_val - b_val
        direction = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  {label:<32} {b_val:>8.{decimals}f} → {c_val:>8.{decimals}f}  Δ {delta:+.{decimals}f} {direction}")

        if key == "complexity_avg" and delta > max_delta_complexity:
            errors.append(f"complexity_avg increased by {delta:+.3f} (limit: {max_delta_complexity:+.3f})")
        elif key == "duplication_pct" and delta > max_delta_duplication:
            errors.append(f"duplication_pct increased by {delta:+.1f}% (limit: {max_delta_duplication:+.1f}%)")
        elif key == "health_score" and delta < max_delta_health:
            errors.append(f"health_score dropped by {delta:+.1f} (limit: {max_delta_health:+.1f})")
        elif key == "dead_code" and c_val > b_val:
            errors.append(f"dead_code increased: {b_val} → {c_val} (must not grow)")

    print()
    if errors:
        print("❌ FAIL: Quality gate exceeded:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("✅ PASS: All metrics within acceptable delta.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--baseline", required=True, help="Path to baseline JSON")
    p.add_argument("--current", required=True, help="Path to current report JSON")
    p.add_argument("--max-delta-complexity", type=float, default=0.5)
    p.add_argument("--max-delta-duplication", type=float, default=3.0)
    p.add_argument("--max-delta-health", type=float, default=-5.0)
    args = p.parse_args()

    baseline = extract_summary(load(args.baseline))
    current = extract_summary(load(args.current))

    return compare(
        baseline=baseline,
        current=current,
        max_delta_complexity=args.max_delta_complexity,
        max_delta_duplication=args.max_delta_duplication,
        max_delta_health=args.max_delta_health,
    )


if __name__ == "__main__":
    sys.exit(main())
