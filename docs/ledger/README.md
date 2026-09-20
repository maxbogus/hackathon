# Decision Ledger

Append-only журнал значимых решений (`decisions.jsonl`) и находок (`findings.jsonl`)
в этом проекте. Используется для:

1. **Не переучивать агента** в каждой сессии — решения накапливаются
2. **Обоснование архитектурных выборов** (почему ML вне Docker, почему LiteLLM)
3. **Презентация** — `make ledger-export` → markdown для слайдов
4. **История для потомков** (включая самих себя через месяц)

## Файлы

- `decisions.jsonl` — архитектурные и продуктовые решения (D-NNN)
- `findings.jsonl` — находки в процессе работы (F-NNN)

## Формат

Одна строка = один JSON. Парсится `json.loads(line)`.

### Decision

```json
{"id": "D-001", "ts": "2026-09-20T15:30:00Z", "title": "...", "context": "...", "decision": "...", "alternatives": ["..."], "consequences": ["..."], "tickets": ["T-042"], "tags": ["architecture"], "links": [".clinerules/10-ml-as-scripts.md"]}
```

### Finding

```json
{"id": "F-001", "ts": "2026-09-20T16:00:00Z", "title": "...", "context": "...", "evidence": "...", "impact": "...", "tickets": ["T-026"], "tags": ["data"]}
```

## Когда писать

| Решение | RICE > 5 | Меняет архитектуру | Записать? |
|---|---|---|---|
| Выбор стека | да | да | ✅ D-NNN |
| Найдена неочевидная особенность данных | — | — | ✅ F-NNN |
| Поменяли цвет кнопки | нет | нет | ❌ |
| Выбрали библиотеку X | да | да | ✅ D-NNN |
| Нашли bug в скрипте | — | — | ✅ F-NNN (тег `bug`) |

## Команды

```bash
make ledger-add       # интерактивное добавление
make ledger-list      # последние 7 дней
make ledger-export    # → docs/ledger/EXPORT.md (для презентации)
make ledger-check     # pre-commit проверка
```

Подробности — в `.clinerules/14-decisions-ledger.md`.

## Promotion (находка → rule → skill)

```
Finding (F-NNN)
   ↓ если локально
Note (docs/notes/NNN-slug.md)
   ↓ если широко применимо
Rule (.clinerules/NN-foo.md)
   ↓ если длинная инструкция
Skill (ai/skills/NN-name.md)
```

```bash
make note-from-finding   # создать note из последней находки
make promote NOTE=001 TARGET=rule
make promote NOTE=001 TARGET=skill
```

См. `.clinerules/15-promote-finding.md`.

## Export для презентации

```bash
make ledger-export
# → docs/ledger/EXPORT.md
```

Используется в слайде "Архитектурные решения" на защите.
