---
id: T-230
phase: 1
title: "backend+frontend: активный набор прогнозов, кандидат и эталон"
priority: P1
effort: 4
unit: hours
rice:
  R: 8
  I: 2.0
  C: 0.8
  score: 3.2
depends_on: [T-229]
blocks: []
tags: [backend, db, frontend, api, alembic]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: "bogusov"
---

# T-230: наборы прогнозов — подмена, кандидат, возврат эталона

## Context

Сгенерированные прогнозы нужно было грузить в БД и «подменять» ими текущие, сохранив
возможность вернуть эталон. Прямая перезапись сделала бы откат невозможным, а второй
набор строк дал бы дубли в чтениях (F-108).

## Acceptance Criteria

- [x] Alembic-миграция: `predictions.is_active/is_etalon` (+индекс), backfill эталона,
      `prediction_runs.{pipeline_kind,row_count,recommendation,error,is_etalon,activated_at}`
      + etalon-run со `holdout_wape_score=0.8751`.
- [x] `app/predictions_active.py`: `active_params`, `activate`, `restore_etalon`,
      `validate_candidate` (clinerule 23 R4), `ingest_candidate`, `build_recommendation`
      (clinerule 24 R3), `feature_state`.
- [x] Эндпоинты: `/predictions/regenerate`, `/predictions/runs`, `/predictions/runs/{id}`,
      `.../ingest`, `.../reject`, `/predictions/restore-etalon`, `/predictions/active`.
- [x] Все чтения (`db/{id}`, `export.csv`, `export.xlsx`, `load`) фильтруют `is_active`
      и берут дефолты из активного набора; `prefer_active=true` — фолбэк фронта.
- [x] UI: панель генерации (кандидат → «Загрузить и сделать активным» / «Оставить эталон»),
      блок «Как это работает», жёлтая подпись фолбэка графика.
- [x] CLI/Makefile: `make predictions-list|activate|restore-etalon|ingest-csv`.

## Verification

```bash
uv run pytest apps/backend/tests/test_predictions_active_t230.py -q --no-cov  # 26 passed
make api-gen && make api-check            # 31 paths, in sync
make predictions-list                     # активный набор + история запусков
curl -sX POST localhost:8000/api/v1/predictions/restore-etalon | jq
```

## Status

`done` (см. D-042, F-108).
