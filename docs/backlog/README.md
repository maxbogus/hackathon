# Backlog — Transit-AI

Все тикеты в YAML frontmatter формате. Скрипты:

```bash
make backlog-ready    # топ-5 ready по RICE
make backlog-list     # все тикеты отсортированные по RICE
make ticket ID=T-042 TITLE="..."  # создать новый тикет
```

## Структура

- `tickets/T-NNN-slug.md` — активные тикеты (status: ready | in-progress | blocked)
- `archive/T-NNN-slug.md` — выполненные (status: done)
- `decisions/0XX-name.md` — ADR (Architecture Decision Records)
- `STATUS.md` — критический путь + статус

## Workflow

1. **Выбрать** тикет: `make backlog-ready`
2. **Пометить** `status: in-progress` в YAML frontmatter
3. **Реализовать** через TDD (см. `.clinerules/16-tdd-cycle.md`)
4. **Проверить** `make check-all`
5. **Закоммить** с Conventional Commits (`feat(scope): ... (T-NNN)`)
6. **Пометить** `status: done` + галочки в Acceptance Criteria
7. **Переместить** в `archive/`
8. **Обновить** `STATUS.md`
9. **Обновить** `docs/HANDOFF.md`

Подробности в `.clinerules/03-backlog-format.md`.

## RICE

`score = (R * I * C) / effort`

Сортировка по score DESC. Top-5 = `make backlog-ready`.

## Критический путь

См. `STATUS.md`. Обновляется после каждого `done`.

## Фазы

| Phase | Что | Готовность |
|---|---|---|
| 0 | Toolchain, clinerules, ledger | 🟡 in progress |
| 1 | Backend skeleton + OpenAPI | ⏳ not started |
| 2 | ML pipeline (scripts + artefacts) | ⏳ not started |
| 3 | Backend ↔ ML contract | ⏳ not started |
| 4 | Frontend (Vite + Orval + Map) | ⏳ not started |
| 5 | LLM Assistant (lawcopilot) | ⏳ not started |
| 6 | MCP draft | ⏳ not started |
| 7 | Docs + QA (Света) | ⏳ not started |
| 8 | CI + polish | ⏳ not started |
