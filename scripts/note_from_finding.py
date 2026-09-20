#!/usr/bin/env python3
"""Создать note в docs/notes/ из последней находки в ledger."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

FINDINGS = Path("docs/ledger/findings.jsonl")
NOTES_DIR = Path("docs/notes")


def slugify(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", slug)[:50]
    return slug


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finding", help="F-NNN (по умолчанию последняя)")
    args = parser.parse_args()

    if not FINDINGS.exists() or FINDINGS.stat().st_size == 0:
        print("❌ Ledger findings пуст. Сначала: make ledger-add --kind=finding")
        return 1

    lines = [l for l in FINDINGS.read_text().splitlines() if l.strip()]
    target = None
    if args.finding:
        for l in lines:
            rec = json.loads(l)
            if rec["id"] == args.finding:
                target = rec
                break
    else:
        target = json.loads(lines[-1])

    if not target:
        print(f"❌ Finding {args.finding} не найден")
        return 1

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(NOTES_DIR.glob("NNN-*.md"))
    if existing:
        next_num = max(int(p.name[:3]) for p in existing) + 1
    else:
        next_num = 1
    slug = slugify(target["title"])
    target_file = NOTES_DIR / f"{next_num:03d}-{slug}.md"

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = f"""# {next_num:03d}: {target['title']}

- **Date:** {date}
- **Source:** {target['id']}
- **Tags:** {', '.join(target.get('tags', []))}

## Finding

{target.get('context', '')}

## Evidence

{target.get('evidence', '')}

## Impact on decisions

{target.get('impact', '')}

## Tickets

{', '.join(target.get('tickets', [])) or '_(не связано с тикетами)_'}
"""
    target_file.write_text(content, encoding="utf-8")
    print(f"✅ Created {target_file}")
    print(f"   Source: {target['id']}")
    print(f"   Next: review and promote with `make promote NOTE={next_num:03d} TARGET=rule|skill`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
