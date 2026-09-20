#!/usr/bin/env python3
"""CLI для работы с docs/ledger/{decisions,findings}.jsonl."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEDGER_DIR = Path("docs/ledger")
DECISIONS = LEDGER_DIR / "decisions.jsonl"
FINDINGS = LEDGER_DIR / "findings.jsonl"


def next_id(kind: str, file: Path) -> str:
    """Следующий свободный id D-NNN или F-NNN."""
    prefix = "D" if kind == "decision" else "F"
    if not file.exists():
        return f"{prefix}-001"
    ids = []
    for line in file.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rec = json.loads(line)
                ids.append(int(rec["id"].split("-")[1]))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return f"{prefix}-{(max(ids, default=0) + 1):03d}"


def cmd_add(args: argparse.Namespace) -> int:
    """Интерактивно добавляет запись."""
    kind = "decision" if args.kind == "decision" else "finding"
    target = DECISIONS if kind == "decision" else FINDINGS
    record_id = args.id or next_id(kind, target)
    ts = datetime.now(timezone.utc).isoformat()

    print(f"Добавляем {record_id} в {target.name}")
    record: dict = {"id": record_id, "ts": ts}
    record["title"] = input("  Title: ").strip()
    record["context"] = input("  Context: ").strip()
    if kind == "decision":
        record["decision"] = input("  Decision: ").strip()
        record["alternatives"] = [
            x.strip() for x in input("  Alternatives (через запятую): ").split(",") if x.strip()
        ]
        record["consequences"] = [
            x.strip() for x in input("  Consequences (через запятую): ").split(",") if x.strip()
        ]
    else:
        record["evidence"] = input("  Evidence: ").strip()
        record["impact"] = input("  Impact: ").strip()
    record["tickets"] = [
        x.strip() for x in input("  Tickets (T-NNN,T-NNN): ").split(",") if x.strip()
    ]
    record["tags"] = [
        x.strip() for x in input("  Tags (через запятую): ").split(",") if x.strip()
    ]

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\n✅ Added {record_id}: {record['title']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Показать записи за последние N дней."""
    if not DECISIONS.exists() and not FINDINGS.exists():
        print("Ledger пуст")
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    total = 0
    for file, kind in [(DECISIONS, "D"), (FINDINGS, "F")]:
        if not file.exists():
            continue
        for line in file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = datetime.fromisoformat(rec["ts"])
            if ts < cutoff:
                continue
            total += 1
            print(f"\n{rec['id']} [{rec['ts']}] {rec['title']}")
            for k in ("decision", "context", "evidence", "impact"):
                if k in rec:
                    val = rec[k][:120] + "..." if len(rec[k]) > 120 else rec[k]
                    print(f"  {k.capitalize()}: {val}")
            if rec.get("tickets"):
                print(f"  Tickets: {', '.join(rec['tickets'])}")
            if rec.get("tags"):
                print(f"  Tags: {', '.join(rec['tags'])}")
    if total == 0:
        print(f"Нет записей за последние {args.days} дней")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Экспорт в markdown."""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decision Ledger Export",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
    ]
    for file, prefix in [(DECISIONS, "## Decision"), (FINDINGS, "## Finding")]:
        if not file.exists():
            continue
        for line in file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            lines.append(f"{prefix} {rec['id']}: {rec['title']}")
            lines.append(f"_{rec['ts']}_")
            lines.append("")
            lines.append(f"**Context:** {rec['context']}")
            lines.append("")
            if "decision" in rec:
                lines.append(f"**Decision:** {rec['decision']}")
                lines.append("")
                if rec.get("alternatives"):
                    lines.append(f"**Alternatives:** {', '.join(rec['alternatives'])}")
                    lines.append("")
                if rec.get("consequences"):
                    lines.append("**Consequences:**")
                    for c in rec["consequences"]:
                        lines.append(f"- {c}")
                    lines.append("")
            else:
                if "evidence" in rec:
                    lines.append(f"**Evidence:** {rec['evidence']}")
                    lines.append("")
                if "impact" in rec:
                    lines.append(f"**Impact:** {rec['impact']}")
                    lines.append("")
            if rec.get("tickets"):
                lines.append(f"**Tickets:** {', '.join(rec['tickets'])}")
                lines.append("")
            if rec.get("tags"):
                lines.append(f"**Tags:** {', '.join(rec['tags'])}")
                lines.append("")
            lines.append("---")
            lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Exported to {output}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Pre-commit проверка: ledger существует и не пуст."""
    if not DECISIONS.exists() or DECISIONS.stat().st_size == 0:
        print("⚠ Ledger пуст. Добавьте решение: make ledger-add")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Добавить запись в ledger")
    p_add.add_argument("--kind", choices=["decision", "finding"], default="decision")
    p_add.add_argument("--id", help="ID (например D-001)")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="Список за период")
    p_list.add_argument("--days", type=int, default=7)
    p_list.set_defaults(func=cmd_list)

    p_export = sub.add_parser("export", help="Экспорт в markdown")
    p_export.add_argument("--output", required=True)
    p_export.set_defaults(func=cmd_export)

    p_check = sub.add_parser("check", help="Pre-commit проверка")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
