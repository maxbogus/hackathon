# 07-workflows.md — Workflow для агентов

## 1. Старт сессии

```bash
# 1. Прочитать HANDOFF.md (если есть)
cat docs/HANDOFF.md

# 2. Посмотреть топ тикетов
make backlog-ready

# 3. Посмотреть текущий статус
cat docs/backlog/STATUS.md

# 4. Посмотреть последние решения в ledger
make ledger-list

# 5. Пометить тикет как in-progress в YAML frontmatter
```

## 2. Разработка тикета (RED → GREEN → REFACTOR)

См. подробнее `.clinerules/16-tdd-cycle.md`. Краткий цикл:

1. **RED:** написать падающий тест в `tests/`
2. **GREEN:** минимальный код, чтобы тест прошёл
3. **REFACTOR:** улучшить код (DRY, типизация, документирование)
4. **VERIFY:** `make check-all`

## 3. Коммит

```bash
# Conventional Commits (enforced by commit-msg hook)
git add apps/backend/app/api/predictions.py tests/test_predictions.py
git commit -m "feat(backend): add predictions endpoint (T-042)

- GET /api/v1/predictions/stop/{id}
- читает ml/artifacts/<active>/ через forecast/loader.py
- возвращает Pydantic-схему PredictionResponse
- кэширует в Redis на 60 секунд

Refs: T-042"
```

Pre-commit hook автоматически:
- Запустит ruff --fix на staged Python файлах
- Запустит prettier --write на staged TS/JSON/YAML/MD
- Проверит что нет .env, артефактов, data/
- Проверит что OpenAPI свежий (если менялся backend)
- Запустит gitleaks (если установлен)

## 4. Push

```bash
git push origin feature/T-042-predictions
```

Pre-push hook автоматически:
- Запустит mypy strict
- Запустит pytest unit tests
- Сгенерит Orval (если менялся OpenAPI) и проверит sync

## 5. PR

```bash
# Создать через GitHub CLI
gh pr create --base main --title "feat(backend): predictions endpoint (T-042)"
```

PR должен содержать:
- Ссылку на тикет в описании
- Список Acceptance Criteria
- Скриншот/curl-output (если визуальное)

## 6. Merge

```bash
gh pr merge --squash --delete-branch
```

После merge:
1. Пометить тикет `status: done` (поставить галочки)
2. Переместить в `docs/backlog/archive/`
3. Если RICE > 5 — запись в ledger уже должна быть (pre-commit проверяет)
4. Обновить `docs/backlog/STATUS.md`

## 7. Завершение сессии (HANDOFF)

**В КАЖДОМ ответе агента** — блок `## CONTEXT HANDOFF` (6 строк):
```
## CONTEXT HANDOFF
- Цель: доделать T-042 (predictions endpoint)
- Состояние: tests написаны (3 passed), implementation WIP
- Последнее решение: использовать forecast/loader.py с JSON Schema валидацией
- Следующая задача: T-042 → написать integration test
- Артефакты на диске: apps/backend/app/forecast/loader.py, tests/test_loader.py
- Открытые вопросы: нужно ли кэширование в Redis (RICE 6.0)
```

**ИЛИ** обновить `docs/HANDOFF.md` (источник истины):
```bash
make handoff-update
```

См. `.clinerules/13-context-transfer.md` для подробностей.

## 8. Promotion (находка → rule → skill)

Если в ходе работы нашёл что-то неочевидное:
1. Записать в `docs/ledger/findings.jsonl` через `make ledger-add` (тег tickets: [T-XXX])
2. Если находка локальная → `docs/notes/NNN-slug.md`
3. Если правило применимо широко → `.clinerules/NN-*.md`
4. Если длинная инструкция → `ai/skills/NN-name.md`

См. `.clinerules/15-promote-finding.md`.

## 9. Не делать

- ❌ Skip pre-commit hook без причины (`--no-verify`)
- ❌ Merge без обновлённого HANDOFF.md (если сессия длинная)
- ❌ Помечать тикет done без `make check-all`
- ❌ Патчить generated/ файлы
- ❌ Использовать npm/pnpm
- ❌ Записывать реальные ключи в .env.example
