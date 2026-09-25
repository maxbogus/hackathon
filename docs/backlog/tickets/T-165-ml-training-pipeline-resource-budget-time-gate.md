---
id: T-165
phase: 2
title: ML training pipeline resource budget + R6 time gate (≤ 60 мин суммарно)
priority: P1
effort: 1.5
unit: hours
rice:
  R: 4
  I: 2.0
  C: 1.0
  score: 5.00
depends_on: []
blocks: []
tags: [ml, training, budget, r6, ci-gate]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-165: ML training pipeline resource budget + R6 time gate

## Context

R6 hackathon-rules:
> "Обучение всех моделей суммарно ≤ 60 минут (на RTX 5060 / 4070)"

Сейчас нет автоматической проверки суммарного времени обучения.
Если обучение превысило R6 лимит — это блокер для submission,
но обнаружится только вручную.

Решение: scripts/check_training_time.py сканирует meta.json во всех артефактах,
суммирует train_time_sec, проверяет ≤ 3600s.

## Acceptance Criteria

- [ ] scripts/check_training_time.py:
  - [ ] CLI: uv run python scripts/check_training_time.py
  - [ ] Сканирует ml/artifacts/*/meta.json
  - [ ] Суммирует поля train_time_sec (или computes from start/end timestamps)
  - [ ] Проверяет ≤ 3600s (60 мин)
  - [ ] Exit 0 при PASS, exit 1 при FAIL
  - [ ] Печатает таблицу: model_id / train_time_sec / cumulative
- [ ] tests/test_check_training_time.py (4+ теста):
  - [ ] Pass при сумме 45 мин
  - [ ] Fail при сумме 75 мин
  - [ ] Pass при пустом каталоге artifacts
  - [ ] Парсинг битого meta.json → warning, skip
  - [ ] Поддержка кастомного лимита через --limit-sec
- [ ] Makefile target check-training-time:
  - [ ] uv run python scripts/check_training_time.py
  - [ ] Включён в check-all
- [ ] make check-all падает если время > 60 мин
- [ ] Makefile target train-baseline использует TRAIN_MEMORY_LIMIT env

## Technical Notes

**scripts/check_training_time.py:**

```python
"""Check cumulative ML training time per R6 hackathon-rules (≤ 60 min).

Usage:
    uv run python scripts/check_training_time.py
    uv run python scripts/check_training_time.py --limit-sec 3600
    uv run python scripts/check_training_time.py --artifacts-dir ml/artifacts
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

R6_LIMIT_SEC = 3600  # 60 min


def scan_artifacts(artifacts_dir: Path) -> list[dict]:
    """Scan meta.json in each model artifact directory."""
    records: list[dict] = []
    if not artifacts_dir.exists():
        return records
    for meta_path in sorted(artifacts_dir.glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError as e:
            print(f"⚠ Skipping {meta_path}: {e}", file=sys.stderr)
            continue
        model_id = meta.get("model_id", meta_path.parent.name)
        train_time = meta.get("train_time_sec", 0)
        records.append({
            "model_id": model_id,
            "train_time_sec": train_time,
            "path": str(meta_path),
        })
    return records


def check_total_time(
    records: list[dict],
    limit_sec: float = R6_LIMIT_SEC,
) -> tuple[bool, float, list[str]]:
    """Return (pass, total_sec, violations)."""
    total = sum(r["train_time_sec"] for r in records)
    violations: list[str] = []
    if total > limit_sec:
        violations.append(
            f"Total training time {total:.0f}s ({total/60:.1f}m) > {limit_sec:.0f}s ({limit_sec/60:.1f}m) — R6 breach"
        )
    return (len(violations) == 0, total, violations)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check R6 training time limit")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("ml/artifacts"))
    parser.add_argument("--limit-sec", type=float, default=R6_LIMIT_SEC)
    args = parser.parse_args()

    print(f"📊 Scanning {args.artifacts_dir} for training time...")
    records = scan_artifacts(args.artifacts_dir)
    if not records:
        print("⚠ No artifacts found. Skipping R6 check.")
        return 0

    print(f"\n{'Model ID':<30} {'Time (sec)':>12} {'Time (min)':>12}")
    print("-" * 60)
    cumulative = 0.0
    for r in records:
        cumulative += r["train_time_sec"]
        print(f"{r['model_id']:<30} {r['train_time_sec']:>12.1f} {r['train_time_sec']/60:>12.2f}")
    print("-" * 60)
    print(f"{'TOTAL':<30} {cumulative:>12.1f} {cumulative/60:>12.2f}")

    passed, total, violations = check_total_time(records, args.limit_sec)
    if passed:
        print(f"\n✅ R6 PASS: training time {total/60:.1f}m ≤ {args.limit_sec/60:.1f}m")
        return 0
    for v in violations:
        print(f"\n❌ {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

**Makefile fragment:**

```makefile
check-training-time: ## R6 gate: суммарное время обучения ≤ 60 мин
	$(UV) run python scripts/check_training_time.py

# В check-all добавить:
check-all: lint typecheck test api-check ledger-check frontend-text-check check-training-time pyscn-compare
```

## Verification

```bash
uv run pytest tests/test_check_training_time.py -v
make check-training-time
# → "✅ R6 PASS: training time 38.2m ≤ 60.0m"
```

## Beneficiary Impact

Жюри (4/5) — R6 compliance.
Команда (4/5) — предотвращение переобучения.

RICE: 5.00 — nice to have, защита от регрессии.
