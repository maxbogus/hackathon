# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-25T10:40:32.655853+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Hackathon submission готов: WAPE-score = **0.8681** на holdout (сен–окт 2025),
что соответствует **максимальным 10/10 баллам** по Критерию 1 (>0.88).
Submission pipeline (T-145) → `make submission` → `predictions/submission.csv`
(14640 строк, формат платформы). Следующие шаги: залить на платформу
(до 27.09 23:59 МСК), затем улучшать до submission с exogenous (T-123, T-124, T-125).

## Прогресс

Phase 2 (ML) critical path готов:
- T-143 RealSource — DataSource для labels_day_*.csv (12 tests, schema validate)
- T-144 WAPE-score в metrics.py — primary метрика (16 tests)
- T-145 submission pipeline → submission.csv (14 640 строк, 8 tests)
- T-136 (year-horizon) + T-140 (GCN-LSTM stop-level) → backlog (отменены орг.)

Submission файл: `predictions/submission.csv` — 14 640 строк,
10 routes × 61 day × 24 hour, separator `;`, формат совпадает с платформой.

**Holdout WAPE-score = 0.8681** (сен–окт 2025), MAE=148.6, WAPE=0.1319, RMSLE=0.4959.
baseline = 0.48 → мы на 0.8681 (в 1.81× лучше baseline).

## Git state

```
commit: d82044c
status: M ml/scripts/make_submission.py
 M ml/tests/test_evaluate.py
 M ml/tests/test_make_submission.py
 M ml/tests/test_metrics.py
 M ml/tests/test_metrics_wape.py
 M ml/tests/test_route_baseline.py
 M ml/transit_ai/reports/metrics.py
?? data/real/README.md
?? "docs/\320\230\320\230-\320\277\321\200\320\276\320\263\320\275\320\276\320\267 \320\267\320\260\320\263\321\200\321\203\320\267\320\272\320\270 \321\202\321\200\320\260\320\274\320\262\320\260\320\271\320\275\321\213\321\205 \320\274\320\260\321\200\321\210\321\200\321\203\321\202\320\276\320\262.pdf"
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-131-dispatcher-alerts-overload-predictions-15.md
- T-133-slide-pain-points-to-solution-mapping-for.md
- T-135-frontend-tanstack-router-role-url-routing.md
- T-141-frontend-text-constants-registry-hybrid.md
- T-142-frontend-typed-config-with-stub-fallback.md

## Архив (done за всё время): 40

- T-131-dispatcher-alerts-overload-predictions-15.md
- T-133-slide-pain-points-to-solution-mapping-for.md
- T-135-frontend-tanstack-router-role-url-routing.md
- T-141-frontend-text-constants-registry-hybrid.md
- T-142-frontend-typed-config-with-stub-fallback.md
_(показаны последние 5 из 40)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-016**: uv как единый package manager: Python локально, в Docker backend, и в ML — везде через uv
- **D-016**: WAPE-score становится primary метрикой хакатона (вместо RMSLE)
- **D-017**: RealSource заменяет SyntheticSource в production pipeline (но SyntheticSource сохраняется для тестов)

## Последние находки

- **F-016**: Организаторы подтвердили: year-horizon не требуется, WAPE-score вместо RMSLE
- **F-017**: WAPE-score требует поддержки корректирующих коэффициентов в API
- **F-018**: Реальный dataset хакатона НЕ полная сетка 24h — трамваи не ходят 0-3 ночи

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
