# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-20T14:45:00+00:00
> Обновлено: вручную (Makefile handoff-target сломан — Makefile:248 missing separator)

## Цель

MVP работающий end-to-end: backend читает ML артефакт, выдаёт прогнозы.
**DONE в этой сессии.**

## Прогресс

- ✅ Phase 0 (toolchain + clinerules + ledger) — 13 тикетов
- ✅ Phase 1 backend skeleton — T-014, T-019, T-020
- ✅ Phase 2 ML pipeline MVP — T-024, T-025, T-027, T-031
- ✅ Phase 3 predictions endpoint — T-042 (MVP, baseline only)
- 🟡 Phase 2/3 next: T-028 (XGBoost), T-029 (GRU), T-030 (Hybrid), T-041 (full synthetic 800/40/2y)

## Git state

```
HEAD: <next commit> (TBD — feat(ml+backend): synthetic + baseline + predictions MVP)
prev: 0d58869 (T-014, T-019, T-020)
prev: e3d7abb (tooling: pyscn + dbml + benchmark + docker)
origin/master: dbc538b
```

## Что сделано в этой сессии

- **Backend skeleton (T-014, T-019, T-020):** FastAPI app, Settings, ArtifactLoader (JSON Schema validation), health endpoints (commit 0d58869).
- **ML foundation (T-024, T-025, T-027, T-031):**
  - DataSource ABC + SyntheticSource (MVP-size: 10 stops × 5 routes × 30 days)
  - Predictor ABC + BaselineMean (mean-by-time-bucket, cold-start global fallback)
  - ModelRegistry (save → meta.json + model.pkl, validate, activate)
- **Predictions endpoint (T-042):** GET /api/v1/predictions/stop/{id} читает активный артефакт, вызывает BaselineMean, возвращает hourly predictions.
- **Schema:** docs/schemas/prediction_artifact.schema.json + example, 6 schema tests.
- **Tests:** 53/53 passed, ruff clean (на новых файлах).

## E2E verified (live)

```bash
$ curl http://localhost:8765/api/v1/models/active
{"model_id":"baseline_v1","kind":"baseline","version":"v0.1.0",...}

$ curl 'http://localhost:8765/api/v1/predictions/stop/1?period_start=2026-02-01T07:00:00&period_end=2026-02-01T10:00:00'
{"stop_id":1,"model_id":"baseline_v1","horizon":"day","granularity":"hour","data":[
  {"value":21.33,"lower":19.25,"upper":23.41}, ... 3 точки
]}
```

## Следующая задача

**T-028 (XGBoost)** — следующий шаг для реального улучшения RMSLE.
Но **сначала починить make handoff-update** (Makefile:248 missing separator) — это блокер для CI.
Либо: запустить make pyscn-compare для оценки качества текущего кода.

## Артефакты на диске (gitignored)

- ml/artifacts/baseline_v1/{meta.json, model.pkl} — реальный артефакт
- ml/artifacts/active.json → {"model_id": "baseline_v1"}

## Известные techdebt

- **F-001:** mypy exclude regex **/__pycache__ invalid (отдельный тикет T-091)
- **Makefile:248** missing separator — make handoff-update сломан, обновлял вручную
- **ruff errors в pre-existing коде** (ml/benchmark/, ml/scripts/, ml/transit_ai/reports/plots.py — 70+ ошибок RUF001 cyrillic/latin и т.п.) — НЕ наш регресс, оставлено как techdebt

## Не делать в следующей сессии

- ❌ Не коммитить .env, ml/artifacts/, data/
- ❌ Не использовать npm install
- ❌ Не патчить сгенерированные файлы
- ❌ Не патчить pre-existing ruff errors в ml/benchmark/ и ml/scripts/
- ❌ Не запускать make handoff-update пока Makefile не починен
