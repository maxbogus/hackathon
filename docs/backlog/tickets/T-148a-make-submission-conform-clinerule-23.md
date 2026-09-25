---
id: T-148a
phase: 2
title: make_submission.py соответствие clinerule 23 — manifest.json + --submission-id + verify
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 2.0
  C: 1.0
  score: 10.0
depends_on: []
blocks: []
tags: [ml, submission, versioning, manifest, hackathon, refactor]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-148a: make_submission.py соответствие clinerule 23

## Context

Сессия 2: задокументировали правило (F-021 + clinerule 23 + skill 03) что submission
должен быть атомарным артефактом с тройкой `(date-range, model-version, run-ts)`
+ обязательный `submission_manifest.json`. Текущий `ml/scripts/make_submission.py`
этому **НЕ соответствует** — пишет только CSV с упрощённым именем
`submission_<model>_<YYYYMMDD_HHMM>.csv`, без манифеста, без submission-id, без
git_commit/dataset_hash/model_uri.

## Acceptance Criteria

- [x] Новый модуль `ml/transit_ai/submission/manifest.py`:
  - `write_manifest(out_dir, ...)` — пишет `submission_manifest.json` со всеми обязательными полями (R2 clinerule 23)
  - `git_commit()` / `git_branch()` — helpers для git-интеграции
  - `dataset_hash(paths)` — sha256 от parquet-файлов (R3 reproducible)
  - `verify_manifest(manifest_path, csv_path)` — R4: проверка что manifest соответствует CSV
- [x] `ml/scripts/make_submission.py` обновлён:
  - Новый аргумент `--submission-id` (default = model_id) — R5
  - Имя CSV по R1: `submission_<model>_<start_date>_<end_date>_<run_ts>.csv`
  - Пишет manifest.json рядом с CSV (R2)
  - `predictions/submission.csv` — копия последнего (R3)
- [x] Тесты `ml/tests/test_submission_manifest.py`:
  - `test_write_manifest_creates_json_file`
  - `test_write_manifest_includes_required_fields`
  - `test_write_manifest_filename_has_three_ids_r1`
  - `test_verify_manifest_passes_on_consistent`
  - `test_verify_manifest_fails_on_missing_file` (exit 1)
  - `test_verify_manifest_fails_on_row_count_mismatch`
- [x] Backward-compatible: существующие вызовы `make submission` без `--submission-id`
  продолжают работать (id = model_id)

## Technical Notes

Шаблон кода и RED-тест уже в `ai/skills/03-submission-pipeline.md`.

Имя CSV по R1:
```
submission_<model_id>_<start>_<end>_<run_ts>.csv
где start/end = YYYYMMDD, run_ts = YYYYMMDDTHHMMSSZ (UTC, ISO compact)
```

## Verification

```bash
# 1. RED: тесты падают (manifest.py не существует)
uv run pytest ml/tests/test_submission_manifest.py -v
# → ModuleNotFoundError или ImportError

# 2. GREEN: реализуем manifest.py → тесты зелёные
uv run pytest ml/tests/test_submission_manifest.py -v
# → 5+ passed

# 3. Запуск скрипта — генерит CSV + manifest
make submission SUBMISSION_ID=v3-manifest-test

# 4. Verify — должно пройти
make submission-verify CSV=predictions/submission_route_baseline_v1_*.csv

# 5. Линт + типы
make lint
```

## Beneficiary Impact

**Департамент (⭐⭐⭐⭐⭐)** — traceability любого submission. Можно за 30 секунд
ответить "какой submission дал WAPE=0.78 на платформе" (R3 reproducible, R8 report).

RICE 10.0 — топ-1 по импакт/effort.
