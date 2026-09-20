# 15-promote-finding.md — Находка → Note → Rule → Skill

## Цикл фиксации знаний

Чтобы **не переучивать агента** в каждой сессии, находки должны
проходить promotion по уровням:

```
[Находка в коде/обсуждении]
       ↓ make ledger-add
[F-NNN в docs/ledger/findings.jsonl]
       ↓ если локальная
[NNN-slug.md в docs/notes/]
       ↓ если правило применимо широко
[NN-foo.md в .clinerules/]
       ↓ если длинная инструкция
[NN-foo.md в ai/skills/]
```

## Уровни

### Level 0: Finding (находка)
- Файл: `docs/ledger/findings.jsonl`
- Формат: одна строка JSON с `id: F-NNN`
- Когда: обнаружили неочевидное свойство системы

```json
{
  "id": "F-001",
  "ts": "2026-09-20T16:00:00Z",
  "title": "Yandex Geocoder API возвращает 403 при превышении лимита 1000/день",
  "context": "...",
  "evidence": "...",
  "impact": "...",
  "tickets": ["T-026"],
  "tags": ["data", "yandex", "bug"]
}
```

### Level 1: Note (заметка)
- Файл: `docs/notes/NNN-slug.md` (из mlaw-rag)
- Формат: структурированный markdown с доказательствами
- Когда: находка локальна для проекта, не требует изменения правил

```markdown
# 001: Yandex Geocoder лимит 1000/день

- **Date:** 2026-09-20
- **Source:** F-001
- **Tags:** data, yandex, rate-limit

## Finding

Yandex Geocoder API возвращает HTTP 403 на 1001-м запросе за сутки.

## Evidence

- Лог: `scripts/logs/geocode.log:1000-OK-1001-403`
- Тест: `ml/tests/test_geocoder.py::test_rate_limit`

## Impact on decisions

- Для bulk-геокодирования (>1000 точек) использовать батчи по 800 с задержкой 1 сек
- Или переключиться на Overpass API (бесплатно, без лимитов)
- См. ADR-003 в `docs/backlog/decisions/`
```

### Level 2: Rule (правило)
- Файл: `.clinerules/NN-slug.md` (нумерация с 16+ для новых)
- Когда: правило применимо ко всем задачам проекта, должно соблюдаться

```markdown
# 16-yandex-rate-limits.md

## Правило

При работе с Yandex API (Maps, Geocoder, Search):
1. Проверяй лимиты в `.env.example` (там есть комментарии)
2. Батчи запросов ≤ 800 в сутки, задержка ≥ 1 сек между батчами
3. При rate-limit — переключись на Overpass (OSM) для bulk-операций

## Где применяется

- `apps/frontend/src/api/geocode.ts`
- `ml/transit_ai/data/real.py` (RealSource геокодер)
- Любой скрипт в `ml/scripts/`
```

### Level 3: Skill (навык)
- Файл: `ai/skills/NN-name.md`
- Когда: длинная инструкция для сложной задачи, которую агент подключает через `use_skill`

```markdown
# Skill: red-green-refactor-tdd

Длинная пошаговая инструкция для TDD цикла.
Подключать через `use_skill("tdd-cycle")` при работе над тикетом.
```

## Автоматизация

```bash
# Создать note из последней находки в ledger
make note-from-finding

# Promote note в rule или skill
make promote NOTE=001 TARGET=rule
make promote NOTE=001 TARGET=skill
```

Скрипт `scripts/promote_note.py`:

```python
"""Promote docs/notes/NNN-slug.md в .clinerules/ или ai/skills/."""
import argparse
import shutil
from pathlib import Path

NOTES_DIR = Path("docs/notes")
CLINERULES_DIR = Path(".clinerules")
SKILLS_DIR = Path("ai/skills")


def find_note(slug: str) -> Path:
    matches = list(NOTES_DIR.glob(f"*{slug}*.md"))
    if not matches:
        raise FileNotFoundError(f"Note with slug {slug!r} not found")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--note", required=True, help="Note slug (e.g. 001)")
    parser.add_argument("--target", choices=["rule", "skill"], required=True)
    args = parser.parse_args()

    note = find_note(args.note)
    if args.target == "rule":
        dest = CLINERULES_DIR / f"{args.note}-{note.stem.split('-', 1)[1]}.md"
    else:
        dest = SKILLS_DIR / f"{args.note}-{note.stem.split('-', 1)[1]}.md"

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(note, dest)
    print(f"✅ Promoted {note.name} → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Когда какой уровень

| Уровень | Пример |
|---|---|
| Finding | "Эта модель лучше работает с feature X" |
| Note | "Yandex Geocoder лимит 1000/день" |
| Rule | "Все запросы к Yandex API батчами ≤ 800" |
| Skill | "Полная инструкция по TDD циклу RED→GREEN→REFACTOR" |

## Когда НЕ надо promote

- ❌ Находка очевидна и описана в официальной документации
- ❌ Находка одноразовая (только для одного тикета)
- ❌ Правило противоречит существующему clinerule (тогда менять старый)

## Don't do

- ❌ Промоутить finding сразу в skill (минуя note и rule)
- ❌ Создавать rule для всего подряд (правил должно быть мало, но они должны быть строгие)
- ❌ Забывать обновить индекс `.clinerules/00-AGENTS.md` при добавлении нового rule
