---
id: T-149
phase: 0
title: clinerule 24 + skill 04 - SUBMISSION CANDIDATE block после каждого ML запуска
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 2.0
  C: 1.0
  score: 10.0
depends_on: [T-148a]
blocks: []
tags: [docs, tooling, ml, submission, hackathon, traceability]
status: in-progress
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-149: SUBMISSION CANDIDATE block — после каждого ML запуска

## Context

F-021 зафиксировал что submission плохо параметризован → пользователь запутался.
T-148a закрыл часть проблемы (manifest.json + R1-R5 clinerule 23).

НО: даже с manifest пользователь должен САМ сравнивать кандидатов и решать
что заливать. Это все еще ручная работа и источник ошибок.

## Решение

После **каждого ML скрипта** который генерит кандидата на submission
(`make train-*`, `make submission`, `make calibrate`, `make diagnose`, ...)
скрипт ОБЯЗАН вывести блок:

```
============================================================
SUBMISSION CANDIDATE
============================================================
CSV:           predictions/submission_<model>_<start>_<end>_<ts>.csv
Manifest:      predictions/submission_<model>_<start>_<end>_<ts>.json
Model:         xgboost_v2
Submission ID: v5-xgboost-features
Holdout WAPE:  0.8123 (+0.080 vs 0.73231 platform prev)
Date range:    2025-11-01 → 2025-12-31
Rows:          14640
Total preds:   13.5M boardings
Recommendation: READY_TO_UPLOAD (BETTER_THAN_PREVIOUS)
Platform prev: 0.73231 (F-023, submission #2)
============================================================
```

Блок парсится регуляркой → можно грепать в логах CI.

## Acceptance Criteria

- [ ] Новый clinerule `.clinerules/24-ml-candidate-output.md` с правилом
- [ ] Новый skill `ai/skills/04-ml-candidate-output.md` с реализацией
- [ ] Helper `ml/transit_ai/submission/candidate.py::print_candidate()` с сигнатурой:
  ```python
  def print_candidate(
      csv_path: Path,
      manifest_path: Path,
      model_id: str,
      submission_id: str,
      holdout_wape: float,
      submission_start: str,
      submission_end: str,
      row_count: int,
      total_predictions: float,
      previous_platform_wape: float | None = None,
      previous_submission_id: str | None = None,
      previous_evidence_id: str | None = None,
  ) -> str:
      ...
  ```
- [ ] helper возвращает строку (для логирования) и печатает в stdout
- [ ] Recommendation enum:
  - `READY_TO_UPLOAD` — holdout лучше предыдущего или нет previous
  - `NEEDS_FIX` — ошибка в данных / row count != expected
  - `WORSE_THAN_PREVIOUS` — holdout хуже → отметить риск
  - `IDENTICAL_TO_PREVIOUS` — тот же holdout (negative result, как F-022)
- [ ] `ml/scripts/make_submission.py` вызывает `print_candidate()` после write_manifest
- [ ] (опционально) `ml/scripts/train_xgboost.py` тоже выводит candidate при retrain
- [ ] Тест `ml/tests/test_candidate.py`:
  - `test_print_candidate_format`
  - `test_recommendation_ready_to_upload`
  - `test_recommendation_worse_than_previous`
  - `test_recommendation_identical`
  - `test_recommendation_needs_fix_on_row_count_mismatch`
- [ ] Обновить `ai/skills/03-submission-pipeline.md` — добавить ссылку на skill 04
- [ ] Обновить `.clinerules/00-AGENTS.md` — добавить clinerule 24 в индекс

## Verification

```bash
uv run pytest ml/tests/test_candidate.py -v --no-cov
make submission SUBMISSION_ID=v5-test
# output должен содержать блок SUBMISSION CANDIDATE
```

## Cross-references

- F-021 (почему правило появилось)
- T-148a (clinerule 23 — manifest.json)
- Clinerule 23 — submission versioning (R1-R5)
- Skill 03 — submission-pipeline
