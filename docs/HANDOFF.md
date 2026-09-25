# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-25T16:23:58.060407+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Продолжить разработку скелета Transit-AI

## Прогресс

Phase 0 (toolchain + clinerules + ledger)

## Git state

```
commit: f83b1c2
status: M ml/tests/test_xgboost_inference.py
 M ml/tests/test_xgboost_route.py
 M ml/transit_ai/models/xgboost_route.py
?? data/real/README.md
```

## Что в работе (2)

- T-149-submission-candidate-block.md
- T-152-xgboost-retrain-with-per-route-lag.md

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

- **F-025**: XGBoost v6 (lag_lookup fallback) на платформе — WAPE=0.12253 vs v5 0.14734 (х уж е)
- **F-026**: WAPE 0.147 — это ОТВРАТИТЕЛЬНО (цель жюри ≥ 0.95, WAPE ≤ 0.05)
- **F-027**: T-153 recursive forecast: holdout WAPE_score=0.0639 vs lookup 0.2129 — в 3.3 раза лучше

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
