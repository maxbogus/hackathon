# Notes — находки с доказательствами

Notes (NNN-slug.md) — формат из `mlaw-rag/.clinerules/11-findings-notes.md`.
Содержат findings с **доказательствами** (числами, не hearsay).

## Когда создавать

Когда находка:
- Неочевидное свойство данных (sentinel значения, кодировки, пропуски)
- Измеренный факт, который отличается от ожиданий
- Решение с измеримым импактом
- Что-то, что будущий читатель откроет заново через боль

## Формат

```markdown
# NNN: <Title>

- **Date:** YYYY-MM-DD
- **Source:** F-NNN (находка в ledger) или T-NNN (тикет)
- **Tags:** data | encoding | pit | chunking | ...

## Finding

Одно предложение: что на самом деле верно.

## Evidence

Числа, команды, code snippets.

## Impact on decisions

Почему это важно для архитектурных/продуктовых решений.
```

## Где хранить

`docs/notes/` (одна заметка = один файл).

## Индекс

`docs/notes/README.md` (этот файл) — каждая заметка = строка в таблице:

| NNN | Title | Source | Date | Tags |
|---|---|---|---|---|
| 001 | Yandex Geocoder лимит 1000/день | F-001 | 2026-09-20 | data, yandex, rate-limit |

## Пример

См. `docs/notes/001-yandex-rate-limits.md` (после T-026).

## Promotion

Если правило применимо ко всем задачам проекта → промоутить в `.clinerules/`:

```bash
make promote NOTE=001 TARGET=rule
```

См. `.clinerules/15-promote-finding.md`.
