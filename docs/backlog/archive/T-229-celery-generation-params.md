---
id: T-229
phase: 3
title: "celery: параметры генерации прогнозов из UI → make_submission.py"
priority: P1
effort: 3
unit: hours
rice:
  R: 8
  I: 2.0
  C: 0.8
  score: 5.3
depends_on: [T-194]
blocks: [T-230]
tags: [celery, ml, backend, features]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: "bogusov"
---

# T-229: Celery-генерация с параметрами (тогглы/zeros/коэффициенты)

## Context

`POST /api/v1/pipeline/full` не принимал тело (нет параметров), а
`predict_window_task` умел только `--submission-id`/`--coef-*`. Тогглы фич
(`feature_toggles`) и обнуления (`zero_overrides`) жили только в БД и не доезжали
до ML-скриптов.

## Acceptance Criteria

- [x] `app/ml_cli.py` — чистый маппинг UI-параметров в CLI:
      тогглы → `flags.yaml` (`--flags-file`), zero_overrides → `--zero-route/--pred-cap/--cap-hours/--zero-weekends/--zero-holidays`.
- [x] `predict_window_task` принимает `feature_flags`, `zero_overrides`, `model_kind`,
      возвращает `csv_path`/`manifest_path`.
- [x] `full_pipeline` форвардит параметры; `POST /pipeline/full` принимает
      опциональное тело `PipelineFullBody`.
- [x] `POST /api/v1/predictions/regenerate` — создаёт `PredictionRun` + `send_task`.
- [x] Мёртвая заглушка `_persist_predictions_to_db` удалена (persistence — T-230).

## Verification

```bash
cd apps/ml_pipeline && uv run pytest tests/ -q --no-cov        # 17 passed
uv run pytest apps/backend/tests -q --no-cov                    # 281 passed
```

## Status

`done` (F-107: `full_pipeline` не годится для тогглов → используем `predict_window`).
