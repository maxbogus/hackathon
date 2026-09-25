# 23-submission-versioning.md — Каждый submission = версионируемый артефакт

## Зачем

`predictions/submission.csv` — это **submission на платформу хакатона**.
Чтобы не перепутать прогоны (что было залито? с какими коэффициентами? на каком коммите?),
каждый submission должен быть **атомарным артефактом** с явной тройкой:

```
submission = (date_range, model_version, run_timestamp) + manifest
```

**Проблема, которая привела к правилу (F-021):**
в `predictions/` оказалось два файла — `submission.csv` и `submission_route_baseline_v1.csv` —
и непонятно, какой был залит на платформу (WAPE 0.72568). Без манифеста нельзя
восстановить ни дату генерации, ни коммит, ни коэффициенты, ни датасет.

## Hard Rules

### R1. Имя файла содержит три идентификатора

```
submission_<model_id>_<start_date>_<end_date>_<run_ts>.csv

Примеры:
  submission_route_baseline_v1_20251101_20251231_20260925T184512Z.csv
  submission_xgboost_v2_20251101_20251231_20260926T103000Z.csv
```

Где:
- `<model_id>` — идентификатор из `ml/artifacts/<model_id>/meta.json`
- `<start_date>` / `<end_date>` — `YYYYMMDD` (НЕ ISO, чтобы не было двоеточий в имени)
- `<run_ts>` — `YYYYMMDDTHHMMSSZ` (UTC, ISO-8601 compact)

`predictions/submission.csv` (без суффиксов) — **convenience alias**,
копия последнего прогона для удобства заливки. **НЕ source-of-truth.**
Создаётся последним шагом пайплайна как `cp` или symlink.

### ⚠️ F-039: НЕ указывать `--output predictions/submission.csv`!

**КРИТИЧНО**: `--output` перезаписывает автоматическое уникальное именование.
С `--output predictions/submission.csv`:
- Создаётся `predictions/submission.csv` (НЕ уникальное имя)
- Manifest имеет `csv_filename: "submission.csv"`
- Платформа может дедуплицировать по имени и вернуть score от старого submission
- Нет traceability — невозможно отследить какой submission залит

**Правильный вызов:**
```bash
# ❌ НЕПРАВИЛЬНО (F-039):
uv run python scripts/make_submission.py --model-id xgboost_v8_poi \
    --output predictions/submission.csv

# ✅ ПРАВИЛЬНО (R1):
uv run python scripts/make_submission.py --model-id xgboost_v8_poi \
    --submission-id v8-poi
# → predictions/submission_xgboost_v8_poi_20251101_20251231_<run_ts>.csv
# → predictions/submission_xgboost_v8_poi_20251101_20251231_<run_ts>.json
```

Если нужно **перезаписать существующий** файл (для repro):
```bash
# ТОЛЬКО если ты понимаешь что делаешь:
uv run python scripts/make_submission.py --model-id xgboost_v8_poi \
    --output predictions/submission_xgboost_v8_poi_20251101_20251231_<existing_ts>.csv
```

### R2. Рядом с CSV обязательно `submission_manifest.json`

Один и тот же basename + расширение `.json`:

```json
{
  "submission_id": "v2-bias-calibration",
  "csv_filename": "submission_route_baseline_v1_20251101_20251231_20260925T184512Z.csv",
  "generated_at": "2026-09-25T18:45:12Z",
  "git_commit": "e64ff08",
  "git_branch": "master",
  "data_source": "RealSource",
  "dataset_hash_sha256": "ab12cd34...",
  "model_id": "route_baseline_v1",
  "model_uri": "ml/artifacts/route_baseline_v1/model.pkl",
  "train_date_range": ["2025-01-01", "2025-08-31"],
  "submission_date_range": ["2025-11-01", "2025-12-31"],
  "row_count": 14640,
  "expected_rows": 14640,
  "total_predictions_sum": 1820456.32,
  "coefficients": {
    "weather": 1.0,
    "event": 1.0,
    "season": 1.0
  },
  "post_processing": ["per_route_log_bias_calibration", "clip_negatives"],
  "platform_submitted": false,
  "platform_score": null,
  "platform_score_submitted_at": null,
  "holdout_wape_score": 0.8751
}
```

`platform_submitted` / `platform_score` обновляются **вручную** после заливки
(F-019 сделал это без автоматизации — на хакатоне нет API для sub).

### R3. Никаких "submission.csv" без манифеста

При добавлении файла в `predictions/`:
1. Запускается `make submission` (или эквивалентный target).
2. Скрипт создаёт файл по правилу R1 **и** manifest.json (R2).
3. Атомарно создаётся `predictions/submission.csv` как копия последнего.

Любой `submission*.csv` без рядом лежащего `submission*.json` —
**считается забытым артефактом**, подлежит удалению через
`make submission-clean` (см. ниже).

### R4. Verifiability: `make submission-verify <csv>`

Target проверяет:
- manifest.json существует рядом с CSV
- в manifest указан ровно тот CSV, что передан аргументом
- dataset_hash совпадает с актуальным `sha256(data/real/*.parquet)`
- git_commit указывает на реальный коммит в истории
- row_count == expected_rows
- формат CSV: `route;date;hour;prediction`, separator=`;`, parseable pandas

Выходит с кодом 1 при любом несовпадении. Используется в CI перед merge.

### R5. Submission-id из `--submission-id` флага

Каждый прогон `make submission` принимает опциональный
`--submission-id <tag>` (например `v2-bias-calibration`).
Значение попадает:
- в `csv_filename` как часть имени (опционально, через суффикс)
- в `submission_manifest.json` поле `submission_id`
- в сообщение коммита: `feat(ml): submission v2-bias-calibration (T-147)`

Без `--submission-id` используется дефолт `<model_id>` как id.

## Команды Makefile

```makefile
submission: ## Сгенерить submission.csv + manifest [WIP: T-NNN]
	@echo "WIP"

submission-verify: ## Проверить manifest рядом с CSV  [WIP: T-NNN]
	@echo "WIP"

submission-clean: ## Удалить CSV без manifest  [WIP: T-NNN]
	@echo "WIP"
```

После реализации (T-148a или подобный) — заменить `@echo` на реальные команды.

## Где применяется

| Файл/компонент | Что менять |
|---|---|
| `ml/scripts/make_submission.py` | Добавить `--submission-id`, генерацию manifest.json, единое имя файла по R1 |
| `scripts/verify_submission.py` | Новый: парсер CSV + manifest + dataset hash + git verify |
| `Makefile` | `submission`, `submission-verify`, `submission-clean` targets |
| `ml/tests/test_make_submission.py` | Тесты: manifest пишется, имя содержит все 3 id, verify падает на mismatch |
| `.gitignore` | `predictions/*.csv` уже игнорируется, `predictions/*.json` тоже |

## Антипаттерны

❌ **Просто `submission.csv` без манифеста** — нельзя понять какой прогон.
❌ **Имя файла только по timestamp** (`submission_20260925T1845.csv`) — потерян model_id.
❌ **Имя файла без даты** (`submission_route_baseline_v1_20260925T1845.csv`) — потерян date-range.
❌ **Manifest пишется отдельно руками** — забываем обновлять `platform_score`.
✅ **Manifest + CSV = один коммит** — атомарность.
✅ **`--submission-id` обязателен для всех submission после этого правила** — иначе нельзя искать в истории.

## Cross-references

- Скилл: `ai/skills/03-submission-pipeline.md` — пошаговая инструкция
- Находка: `F-021` в `docs/ledger/findings.jsonl`
- Решение: `D-NNN` (планируется) — формализация параметризации submission
- Шаблон: `ml/scripts/make_submission.py` — что дописать для соответствия правилу
- Тикет: `T-148a-submission-manifest-and-versioning.md` (планируется)
