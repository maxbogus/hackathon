#!/usr/bin/env python3
"""Promote docs/notes/NNN-slug.md в .clinerules/ или ai/skills/."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

NOTES_DIR = Path("docs/notes")
CLINERULES_DIR = Path(".clinerules")
SKILLS_DIR = Path("ai/skills")


def find_note(slug: str) -> Path | None:
    """Ищет по slug или по NNN."""
    if slug.isdigit():
        matches = list(NOTES_DIR.glob(f"{int(slug):03d}-*.md"))
    else:
        matches = list(NOTES_DIR.glob(f"*{slug}*.md"))
    return matches[0] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--note", required=True, help="Note slug или NNN")
    parser.add_argument("--target", choices=["rule", "skill"], required=True)
    args = parser.parse_args()

    note = find_note(args.note)
    if not note:
        print(f"❌ Note {args.note!r} не найден в {NOTES_DIR}")
        return 1

    # Извлечь slug из имени файла (NNN-slug.md)
    m = re.match(r"^\d{3}-(.+)\.md$", note.name)
    if not m:
        print(f"❌ Имя файла не соответствует NNN-slug.md: {note.name}")
        return 1
    slug = m.group(1)

    if args.target == "rule":
        dest_dir = CLINERULES_DIR
        # Использовать следующий доступный номер (17+)
        existing = sorted(dest_dir.glob("[0-9][0-9]-*.md"))
        next_num = max(int(p.name[:2]) for p in existing) + 1 if existing else 17
        dest = dest_dir / f"{next_num:02d}-{slug}.md"
    else:
        dest_dir = SKILLS_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        # skills начинаются с NN-
        existing = sorted(dest_dir.glob("[0-9][0-9]-*.md"))
        next_num = max(int(p.name[:2]) for p in existing) + 1 if existing else 1
        dest = dest_dir / f"{next_num:02d}-{slug}.md"

    shutil.copy(note, dest)
    print(f"✅ Promoted {note.name} → {dest}")
    print(f"   Next: отредактируй {dest}, добавь header как у других clinerules")
    print(f"   И обнови индекс в .clinerules/00-AGENTS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
