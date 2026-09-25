# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-25T14:16:42.051290+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Продолжить разработку скелета Transit-AI

## Прогресс

Phase 0 (toolchain + clinerules + ledger)

## Git state

```
commit: dad34f9
status: A  data/real/README.md
M  docs/HACKATHON_CHECKLIST.md
M  docs/backlog/STATUS.md
M  docs/backlog/archive/T-137-docs-hackathon-checklist-r8-submission.md
R  docs/backlog/tickets/T-167-hackathon-checklist-sla-resources-loadtest.md -> docs/backlog/archive/T-167-hackathon-checklist-sla-resources-loadtest.md
 D docs/backlog/tickets/T-164-backend-dockerfile-non-root-hardening.md
 D docs/backlog/tickets/T-166-clinerule-22-skill-02-load-testing-playbook.md
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-160-backend-load-test-k6-docker-smoke.md
- T-162-backend-load-profiles-baseline-stress-spike-soak.md
- T-164-backend-dockerfile-non-root-hardening.md
- T-166-clinerule-22-skill-02-load-testing-playbook.md
- T-167-hackathon-checklist-sla-resources-loadtest.md

## Архив (done за всё время): 46

- T-160-backend-load-test-k6-docker-smoke.md
- T-162-backend-load-profiles-baseline-stress-spike-soak.md
- T-164-backend-dockerfile-non-root-hardening.md
- T-166-clinerule-22-skill-02-load-testing-playbook.md
- T-167-hackathon-checklist-sla-resources-loadtest.md
_(показаны последние 5 из 46)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-020**: SLA p95 ≤ 2000ms как hard gate в make check-all (R6 compliance)
- **D-021**: Container resources hardcoded в docker-compose для R3 reproducible
- **D-022**: Dockerfile hardening: multi-stage + non-root user + production healthcheck

## Последние находки

- **F-017**: WAPE-score требует поддержки корректирующих коэффициентов в API
- **F-018**: Реальный dataset хакатона НЕ полная сетка 24h — трамваи не ходят 0-3 ночи
- **F-019**: Первый сабмит submission.csv на платформе хакатона — WAPE-score=0.72568

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
