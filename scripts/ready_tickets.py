#!/usr/bin/env python3
"""Показать тикеты из docs/backlog/tickets/ отсортированные по RICE."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TICKETS_DIR = Path("docs/backlog/tickets")


def parse_ticket(path: Path) -> dict | None:
    """Простой парсер YAML frontmatter (без зависимостей)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm = text[4:end]
    record: dict = {"path": path, "title": "", "tags": []}
    for line in fm.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line.strip())
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key in ("R", "I", "C", "score", "effort", "phase"):
            try:
                record[key] = float(value) if key != "phase" else int(value)
            except ValueError:
                record[key] = 0
        elif key in ("id", "title", "status", "priority"):
            record[key] = value.strip('"')
        elif key == "tags":
            record[key] = [x.strip().strip('"') for x in value.strip("[]").split(",") if x.strip()]
        elif key == "depends_on":
            record[key] = [x.strip().strip('"') for x in value.strip("[]").split(",") if x.strip()]
        else:
            record[key] = value
    # Title из тела файла
    body = text[end + 4 :].lstrip("\n")
    first_h1 = re.search(r"^#\s*(.+)$", body, re.MULTILINE)
    record["title"] = first_h1.group(1).strip() if first_h1 else record.get("title", "")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=5, help="Top N ready")
    parser.add_argument("--all", action="store_true", help="All by RICE")
    args = parser.parse_args()

    if not TICKETS_DIR.exists():
        print("No tickets yet. Создай: make ticket ID=T-001 TITLE=...")
        return 0

    tickets = []
    for f in TICKETS_DIR.glob("T-*.md"):
        rec = parse_ticket(f)
        if rec:
            tickets.append(rec)
    if not tickets:
        print("No tickets yet.")
        return 0

    tickets.sort(key=lambda r: -r.get("score", 0))

    if args.all:
        print("📋 Все тикеты (sorted by RICE):\n")
        for t in tickets:
            print(f"  {t['id']:10} score={t.get('score', 0):6.2f} status={t['status']:12} {t['title'][:60]}")
        return 0

    ready = [t for t in tickets if t.get("status") == "ready"]
    print(f"🔥 Top-{args.top} READY тикетов по RICE:\n")
    for t in ready[: args.top]:
        print(f"  {t['id']:10} score={t.get('score', 0):6.2f} effort={t.get('effort', '?')}h  {t['title'][:60]}")
    if not ready:
        print("  Нет тикетов со статусом 'ready'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
