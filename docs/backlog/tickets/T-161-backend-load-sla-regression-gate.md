---
id: T-161
phase: 1
title: SLA regression gate — парсинг k6 JSON + блокировка make check-all при p95 > 2s
priority: P0
effort: 2
unit: hours
rice:
  R: 6
  I: 3.0
  C: 1.0
  score: 6.00
depends_on: [T-160]
blocks: [T-167]
tags: [backend, loadtest, sla, ci-gate, r6]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-161: SLA regression gate (CI gate на load test)

## Context

T-160 даёт k6 + JSON-репорт, но **нет автоматической проверки SLA**.
Если разработчик забудет запустить `loadtest-smoke` или проигнорирует
нарушение p95 — регрессия попадёт в main. Нужен **CI gate** в `make check-all`.

**Решение:** Python-скрипт парсит JSON-репорт k6, извлекает p50/p95/p99
и error_rate, проверяет SLA, exit 1 при FAIL.

## Acceptance Criteria

- [ ] `scripts/check_load_sla.py`:
  - [ ] CLI: `python check_load_sla.py <json_report>`
  - [ ] Парсит JSON-репорт k6 (структура: `metrics.http_req_duration.values.p(95)`)
  - [ ] Проверяет:
    - `p95_latency_ms ≤ 2000` (R6 SLA)
    - `error_rate ≤ 0.01` (1% допуск)
  - [ ] Печатает таблицу: p50 / p95 / p99 / errors / SLA verdict
  - [ ] Exit 0 при PASS, exit 1 при FAIL
  - [ ] Поддерживает `--report` (последний `docs/load-profiles/reports/*.json`)
- [ ] `tests/test_check_load_sla.py` (6+ тестов):
  - [ ] Pass при p95=1.5s, error_rate=0.5%
  - [ ] Fail при p95=2.5s (SLA breach)
  - [ ] Fail при error_rate=5%
  - [ ] Парсинг битого JSON → exit 1
  - [ ] Отсутствие файла → exit 1 с понятной ошибкой
  - [ ] Кастомные thresholds через `--p95-ms`, `--error-rate`
- [ ] `Makefile` target `loadtest-check`:
  - [ ] Запускает `uv run python scripts/check_load_sla.py docs/load-profiles/reports/<latest>.json`
  - [ ] Включён в `check-all`
- [ ] `make check-all` падает если последний load test показал FAIL

## Technical Notes

**scripts/check_load_sla.py:**

```python
"""Parse k6 JSON report and verify SLA thresholds (R6 hackathon-rules).

Usage:
    uv run python scripts/check_load_sla.py <json_report>
    uv run python scripts/check_load_sla.py --latest
    uv run python scripts/check_load_sla.py --p95-ms 1500 <report>

R6 SLA: p95 ≤ 2000ms, error_rate ≤ 1%.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SLA_P95_MS = 2000
SLA_ERROR_RATE = 0.01


def parse_k6_report(path: Path) -> dict:
    """Extract metrics from k6 JSON summary."""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse {path}: {e}", file=sys.stderr)
        sys.exit(1)

    metrics = data.get("metrics", {})
    duration = metrics.get("http_req_duration", {}).get("values", {})
    failed = metrics.get("http_req_failed", {}).get("values", {})

    return {
        "p50_ms": duration.get("p(50)", 0.0),
        "p95_ms": duration.get("p(95)", 0.0),
        "p99_ms": duration.get("p(99)", 0.0),
        "avg_ms": duration.get("avg", 0.0),
        "error_rate": failed.get("rate", 0.0),
        "total_requests": metrics.get("http_reqs", {}).get("values", {}).get("count", 0),
    }


def check_sla(
    report: dict,
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
    reports = sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not reports:
        print(f"❌ No reports found in {reports_dir}", file=sys.stderr)
        sys.exit(1)
    return reports[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check k6 load test SLA")
    parser.add_argument("report", nargs="?", type=Path, help="k6 JSON report path")
    parser.add_argument("--latest", action="store_true", help="Use latest report")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("docs/load-profiles/reports"),
    )
    parser.add_argument("--p95-ms", type=float, default=SLA_P95_MS)
    parser.add_argument("--error-rate", type=float, default=SLA_ERROR_RATE)
    args = parser.parse_args()

    if args.latest or args.report is None:
        report_path = latest_report(args.reports_dir)
    else:
        report_path = args.report

    print(f" Checking SLA: {report_path}")
    metrics = parse_k6_report(report_path)
    print(f"   p50={metrics['p50_ms']:.1f}ms  p95={metrics['p95_ms']:.1f}ms  "
          f"p99={metrics['p99_ms']:.1f}ms  avg={metrics['avg_ms']:.1f}ms")
    print(f"   errors={metrics['error_rate']:.2%}  requests={metrics['total_requests']}")

    passed, violations = check_sla(metrics, args.p95_ms, args.error_rate)
    if passed:
        print("✅ SLA PASS")
        return 0
    for v in violations:
        print(f"❌ {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## Verification

```bash
# 1. Tests
uv run pytest tests/test_check_load_sla.py -v

# 2. Запуск на реальном отчёте (после make loadtest-smoke)
make loadtest-smoke  # генерит JSON
make loadtest-check  # → "✅ SLA PASS" или "❌ p95=2.5s > 2000ms"
```

## Beneficiary Impact

**Команда (⭐⭐⭐⭐⭐)** — регрессии SLA ловятся ДО merge.
**Жюри (⭐⭐⭐⭐)** — доказательство процесса quality assurance.

RICE: 6.00 — обязательный компонент для submission verification.
