# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-25T14:45:14.923610+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Поднять WAPE submission с 0.72568 → 0.73231 (T-147) → 0.78-0.80 (T-152 XGBoost) до дедлайна 27.09. Frontend coef-slider для К2.в, README Handover

## Прогресс

T-146+T-147 backend done. Submission #2 готов с bias correction. Frontend deferred (слайдеры coef_weather/event/season). Open: T-148 calendar, T-123 weather, T-115 README Handover, frontend coef slider.

## Git state

```
commit: 47daf59
status: M docs/HANDOFF.md
?? data/real/README.md
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-160-backend-load-test-k6-docker-smoke.md
- T-162-backend-load-profiles-baseline-stress-spike-soak.md
- T-164-backend-dockerfile-non-root-hardening.md
- T-166-clinerule-22-skill-02-load-testing-playbook.md
- T-167-hackathon-checklist-sla-resources-loadtest.md

## Архив (done за всё время): 48

- T-160-backend-load-test-k6-docker-smoke.md
- T-162-backend-load-profiles-baseline-stress-spike-soak.md
- T-164-backend-dockerfile-non-root-hardening.md
- T-166-clinerule-22-skill-02-load-testing-playbook.md
- T-167-hackathon-checklist-sla-resources-loadtest.md
_(показаны последние 5 из 48)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-021**: Container resources hardcoded в docker-compose для R3 reproducible
- **D-022**: Dockerfile hardening: multi-stage + non-root user + production healthcheck
- **D-023**: Per-route bias calibration в log-space (T-147): pred *= exp(median(log1p(actual) - log1p(pred)))

## Последние находки

- **F-018**: Реальный dataset хакатона НЕ полная сетка 24h — трамваи не ходят 0-3 ночи
- **F-019**: Первый сабмит submission.csv на платформе хакатона — WAPE-score=0.72568
- **F-020**: Per-route WAPE диагностика (T-146): слабые маршруты [25, 50, 7, 28], слабые часы [0-4, 22-23], слабые weekday [Сб, Вс]

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
