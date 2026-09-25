"""Parse k6 JSON report and verify SLA thresholds (R6 hackathon-rules).

Usage:
    uv run python scripts/check_load_sla.py <json_report>
    uv run python scripts/check_load_sla.py --latest
    uv run python scripts/check_load_sla.py --p95-ms 1500 <report>

R6 SLA: p95 <= 2000ms, error_rate <= 1%.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SLA_P95_MS = 2000.0
SLA_ERROR_RATE = 0.01


def parse_k6_report(path: Path) -> dict[str, float | int]:
    """Extract metrics from k6 JSON summary."""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"Failed to parse {path}: {e}", file=sys.stderr)
        sys.exit(1)

    metrics = data.get("metrics", {})
    duration = metrics.get("http_req_duration", {}).get("values", {})
    failed = metrics.get("http_req_failed", {}).get("values", {})

    return {
        "p50_ms": duration.get("p(50)", 0.0),
        "p95_ms": duration.get("p(95)", 0.0),
        "p99_ms": duration.get("p(99)", 0.0),
        "avg_ms": duration.get("avg", 0.0),
        "max_ms": duration.get("max", 0.0),
        "error_rate": failed.get("rate", 0.0),
        "total_requests": metrics.get("http_reqs", {}).get("values", {}).get("count", 0),
    }


def check_sla(
    report: dict[str, float | int],
    p95_limit_ms: float = SLA_P95_MS,
    error_rate_limit: float = SLA_ERROR_RATE,
) -> tuple[bool, list[str]]:
    """Return (pass, violations)."""
    violations: list[str] = []
    if report["p95_ms"] > p95_limit_ms:
        violations.append(
            f"p95={report['p95_ms']:.1f}ms > {p95_limit_ms:.0f}ms (R6 SLA breach)"
        )
    if report["error_rate"] > error_rate_limit:
        violations.append(
            f"error_rate={report['error_rate']:.2%} > {error_rate_limit:.2%}"
        )
    return (len(violations) == 0, violations)


def latest_report(reports_dir: Path) -> Path:
    """Find most recent k6 JSON report."""
    if not reports_dir.exists():
        print(f"Reports dir {reports_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    reports = sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not reports:
        print(f"No JSON reports found in {reports_dir}", file=sys.stderr)
        sys.exit(1)
    return reports[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check k6 load test SLA (R6)")
    parser.add_argument("report", nargs="?", type=Path, help="k6 JSON report path")
    parser.add_argument("--latest", action="store_true", help="Use latest report from reports dir")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("docs/load-profiles/reports"),
    )
    parser.add_argument("--p95-ms", type=float, default=SLA_P95_MS,
                        help=f"p95 threshold (default: {SLA_P95_MS}ms per R6)")
    parser.add_argument("--error-rate", type=float, default=SLA_ERROR_RATE,
                        help=f"Error rate threshold (default: {SLA_ERROR_RATE:.0%})")
    args = parser.parse_args()

    if args.latest or args.report is None:
        report_path = latest_report(args.reports_dir)
    else:
        report_path = args.report

    print(f"Checking SLA: {report_path}")
    metrics = parse_k6_report(report_path)
    print(f"   p50={metrics['p50_ms']:.1f}ms  p95={metrics['p95_ms']:.1f}ms  "
          f"p99={metrics['p99_ms']:.1f}ms  avg={metrics['avg_ms']:.1f}ms  max={metrics['max_ms']:.1f}ms")
    print(f"   errors={metrics['error_rate']:.2%}  requests={metrics['total_requests']}")

    passed, violations = check_sla(metrics, args.p95_ms, args.error_rate)
    if passed:
        print("SLA PASS")
        return 0
    for v in violations:
        print(f"FAIL: {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
