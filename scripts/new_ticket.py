#!/usr/bin/env python3
"""Создать тикет в docs/backlog/tickets/ по YAML frontmatter шаблону."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

TICKETS_DIR = Path("docs/backlog/tickets")
TEMPLATE = '''---
id: {id}
phase: {phase}
title: {title}
priority: {priority}
effort: {effort}
unit: hours
rice:
  R: {r}
  I: {i}
  C: {c}
  score: {score}
depends_on: [{depends_on}]
blocks: []
tags: [{tags}]
status: ready
created: {today}
updated: {today}
assignee: ""
---

# {id}: {title}

## Context

Why this task exists.

## Acceptance Criteria

- [ ] criterion 1
- [ ] criterion 2

## Technical Notes

Implementation hints.

## Verification

```bash
make ...
```
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="ID (T-NNN)")
    parser.add_argument("--title", required=True, help="Short title")
    parser.add_argument("--phase", default="0", help="Phase (0..8)")
    parser.add_argument("--priority", default="P2", choices=["P0", "P1", "P2"])
    parser.add_argument("--effort", type=int, default=4)
    parser.add_argument("--r", type=int, default=3, help="Reach")
    parser.add_argument("--i", type=float, default=1.0, help="Impact")
    parser.add_argument("--c", type=float, default=0.5, help="Confidence")
    parser.add_argument("--depends-on", default="", help="Comma-separated T-IDs")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    args = parser.parse_args()

    score = round((args.r * args.i * args.c) / max(args.effort, 1), 3)
    slug = args.title.lower().replace(" ", "-").replace("/", "-")[:50]
    filename = f"{args.id}-{slug}.md"
    target = TICKETS_DIR / filename

    if target.exists():
        print(f"❌ Тикет {filename} уже существует")
        return 1

    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    content = TEMPLATE.format(
        id=args.id,
        title=args.title,
        phase=args.phase,
        priority=args.priority,
        effort=args.effort,
        r=args.r,
        i=args.i,
        c=args.c,
        score=score,
        depends_on=", ".join(args.depends_on.split(",")) if args.depends_on else "",
        tags=", ".join(args.tags.split(",")) if args.tags else "",
        today=date.today().isoformat(),
    )
    target.write_text(content, encoding="utf-8")
    print(f"✅ Created {target}")
    print(f"   RICE score: {score}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
