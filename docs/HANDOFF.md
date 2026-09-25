# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-25T20:45:00+00:00
> Обновлено: Cline (агент) после T-172 + T-173 (events features + CatBoost blend)

## Цель

Улучшить прогноз пассажиропотока трамваев к 27.09.2026 через (a) feature engineering
по инфраструктурным событиям сентября-октября 2025 + (b) CatBoost-blend с XGBoost.

## Прогресс

Phase 0-2 завершены. **T-172 + T-173 закоммичены (commit 2b63f08)**, holdout lift
**+2.96pp calibrated** (0.8751 → 0.9047) по сравнению с baseline v8_poi.

## Git state

```
commit: 2b63f08
status: M docs/HANDOFF.md docs/ledger/* docs/backlog/tickets/T-17*
         M ml/transit_ai/models/xgboost_route.py
         A ml/transit_ai/data/events_calendar.py
         A ml/transit_ai/blend/rank_average.py
         A ml/transit_ai/models/catboost_route.py
         A ml/scripts/blend.py ml/scripts/train_catboost.py
         A ml/tests/test_blend.py ml/tests/test_catboost_route.py ml/tests/test_events_calendar.py
         A data/external/events_moscow.json
         A .clinerules/29-zsh-shell-quirks.md
?? predictions/submission_*.csv (148 шт)
```

## Что сделано (последние 5)

- **T-173** — CatBoostRoutePredictor + weighted-mean blend (XGB v9_events + CatBoost v1)
  - ml/transit_ai/blend/rank_average.py: weighted_mean_blend + rank_average_blend
  - ml/transit_ai/models/catboost_route.py: интерфейс как XGBoostRoutePredictor
  - ml/scripts/blend.py + train_catboost.py: entry points
  - 14 новых тестов (4+4+6), все 41/41 зелёные
  - Holdout: 0.8751 (XGB) → 0.9047 (blend calibrated) = **+2.96pp**
- **T-172** — events features (Троицкая, кампус Бауманки, route 90, и др.)
  - 8 событий в data/external/events_moscow.json
  - decay-weighted фичи (exp(-Δt/τ)) в ml/transit_ai/data/events_calendar.py
  - 4 новых фичи в XGBoostRoutePredictor
  - Holdout raw: 0.9027 → 0.9051 (+0.24pp)
  - 15 новых тестов
- **clinerule 29** — zsh-shell-quirks (hard rule для shell-команд)
- T-160..T-167: load testing + SLA gate (D-021..D-023)

## Что в работе

Ничего — ждём следующего тикета. Priority order:
1. Залить v10-blend submission (READY_TO_UPLOAD, holdout 0.9047)
2. Если останется время — T-171 (presentation, deployment, README, demo video)

## Следующая задача

**T-171: deadline-prep-48h-pitch-deploy.md** (in-progress с утра, 27.09 deadline).
Команда запуска:
```bash
make backlog-ready
```

## Открытые вопросы

- **Заливать ли v10-blend?** Holdout 0.9047 > 0.8751 best, manifest verify PASSED.
  F-040 (drift) — local vs platform может быть -0.143pp (см. submission #8 vs holdout).
  Но +2.96pp локально — значимо. **Рекомендация: залить, мониторить platform score.**
- **LightGBM в ensemble?** weighted-mean с 3 моделями может дать ещё +0.5pp, но R6 time limit
  (обучение ≤60 мин суммарно). Сейчас не делаем.
- **Presentation / pitch:** T-171 in-progress, 10 слайдов за 5 минут, видео 2-3 мин.

## Артефакты на диске

- `ml/artifacts/xgboost_v9_events/` — best raw XGBoost (wape_score=0.9051)
- `ml/artifacts/catboost_v1/` — CatBoost (wape_score=0.8951)
- `ml/artifacts/xgboost_v8_poi/` — предыдущий best (wape_score=0.9027)
- `predictions/submission_xgboost_v9_events_*.csv` — XGBoost submission (READY_TO_UPLOAD)
- `predictions/submission_blend_xgboost_v9_events_catboost_v1_20260925T204149Z.csv` — **best** (READY_TO_UPLOAD, 0.9047)
- `docs/ledger/decisions.jsonl` — 29 решений (D-001..D-028)
- `docs/ledger/findings.jsonl` — 44 находки (F-001..F-047)

## Последние решения в ledger

- **D-027**: zsh-shell-quirks → clinerule 29 (hard rule)
- **D-028**: weighted-mean (не rank-average) для count data с пиками

## Последние находки

- **F-046**: events features +0.24pp raw (0.9027 → 0.9051)
- **F-047**: blend +2.96pp calibrated (0.8751 → 0.9047)

## Не делать в следующей сессии

- ❌ Не использовать `python3 -c "..."` с f-string (zsh ломает — см. clinerule 29)
- ❌ Не использовать `sed`/`heredoc` для правок Python файлов — использовать editor tool
- ❌ Не заливать submission без sanity-check 5 критериев (clinerule 28)
- ❌ Не патчить сгенерированные файлы в `apps/frontend/src/generated/`
- ❌ Не коммитить `.env`, `ml/artifacts/`, `predictions/`, `data/` (всё в .gitignore)
- ❌ Не использовать `pip install` / `npm install` / `pnpm install` (только uv / yarn)
- ❌ Не обучать модели в Docker (только скриптами через make)
