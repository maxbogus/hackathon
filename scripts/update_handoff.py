#!/usr/bin/env python3
"""Обновить docs/HANDOFF.md."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HANDOFF = Path("docs/HANDOFF.md")
TICKETS_DIR = Path("docs/backlog/tickets")
LEDGER_DECISIONS = Path("docs/ledger/decisions.jsonl")
LEDGER_FINDINGS = Path("docs/ledger/findings.jsonl")


def run(cmd: str, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            cwd=cwd or Path.cwd(),
            check=False,
        )
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"<error: {e}>"


def load_recent_ledger(path: Path, n: int = 3) -> list[dict]:
    if not path.exists():
        return []
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    records = []
    for line in lines[-n:]:
        import json
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", default="Продолжить разработку скелета Transit-AI")
    parser.add_argument("--progress", default="Phase 0 (toolchain + clinerules + ledger)")
    args = parser.parse_args()

    # Собрать данные
    git_commit = run("git rev-parse --short HEAD")
    git_status = run("git status --short")
    in_progress = []
    done = []
    if TICKETS_DIR.exists():
        import re
        for f in sorted(TICKETS_DIR.glob("T-*.md")):
            text = f.read_text(encoding="utf-8")
            if "status: in-progress" in text:
                in_progress.append(f.name)
            if "status: done" in text:
                done.append(f.name)
    recent_d = load_recent_ledger(LEDGER_DECISIONS, 3)
    recent_f = load_recent_ledger(LEDGER_FINDINGS, 3)

    now = datetime.now(timezone.utc).isoformat()
    content = f"""# HANDOFF — Transit-AI

> Последнее обновление: {now}
> Обновлено: автоматически через `make handoff-update`

## Цель

{args.goal}

## Прогресс

{args.progress}

## Git state

```
commit: {git_commit}
status: {git_status or 'clean'}
```

## Что в работе ({len(in_progress)})

{chr(10).join('- ' + t for t in in_progress) or '_пусто_'}

## Что сделано ({len(done)})

{chr(10).join('- ' + t for t in done) or '_пусто_'}

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

{chr(10).join(f"- **{r['id']}**: {r['title']}" for r in recent_d) or '_пусто_'}

## Последние находки

{chr(10).join(f"- **{r['id']}**: {r['title']}" for r in recent_f) or '_пусто_'}

## Открытые вопросы

(заполняется вручную или через `make ledger-add` с тегом `open-question`)

## Артефакты на диске

- `docs/ledger/decisions.jsonl` — решения (RICE > 5)
- `docs/ledger/findings.jsonl` — находки
- `docs/api/openapi.json` — генерируется backend (`make api-gen`)
- `apps/frontend/src/generated/` — Orval-генерация (`make fe-gen`)
- `ml/artifacts/` — обученные модели (gitignored)
- `predictions/` — прогнозы (gitignored)

## Не делать в следующей сессии

- ❌ Не патчить сгенерированные файлы в `apps/frontend/src/generated/`
- ❌ Не коммитить `.env`, `ml/artifacts/`, `predictions/`, `data/`
- ❌ Не использовать `npm install` или `pnpm install`
- ❌ Не читать `yarn.lock` / `uv.lock` в контекст
- ❌ Не пропускать pre-commit hook без причины
"""
    HANDOFF.write_text(content, encoding="utf-8")
    print(f"✅ Updated {HANDOFF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
