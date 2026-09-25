# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-25T11:29:42.026284+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Продолжить разработку скелета Transit-AI

## Прогресс

Phase 0 (toolchain + clinerules + ledger)

## Git state

```
commit: db1567f
status: M docker-compose.yml
 D docs/backlog/tickets/T-164-backend-dockerfile-non-root-hardening.md
 D docs/backlog/tickets/T-166-clinerule-22-skill-02-load-testing-playbook.md
 M pyproject.toml
 M tests/test_clinerule_index.py
 M tests/test_dockerfile_hardening.py
 M tests/test_load_profiles.py
?? data/real/README.md
?? docs/load-profiles/
?? scripts/check_load_sla.py
?? scripts/check_training_time.py
?? tests/test_check_load_sla.py
?? tests/test_check_training_time.py
?? tests/test_compose_resources.py
?? tests/test_loadtest_makefile.py
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-141-frontend-text-constants-registry-hybrid.md
- T-142-frontend-typed-config-with-stub-fallback.md
- T-162-backend-load-profiles-baseline-stress-spike-soak.md
- T-164-backend-dockerfile-non-root-hardening.md
- T-166-clinerule-22-skill-02-load-testing-playbook.md

## Архив (done за всё время): 43

- T-141-frontend-text-constants-registry-hybrid.md
- T-142-frontend-typed-config-with-stub-fallback.md
- T-162-backend-load-profiles-baseline-stress-spike-soak.md
- T-164-backend-dockerfile-non-root-hardening.md
- T-166-clinerule-22-skill-02-load-testing-playbook.md
_(показаны последние 5 из 43)_

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
