# Skill: Hackathon platform submission workflow

Использовать через `use_skill("hackathon-platform-workflow")` когда нужно
заливать submission на платформу или анализировать local-vs-platform drift.

## Контекст

На хакатоне Transit-AI (tram forecast) каждое улучшение модели = новый submission
на платформу жюри. Submission pipeline:
1. Train модель (XGBoost/GRU/Hybrid) с новыми фичами
2. Generate CSV (14640 строк: 10 routes × 61 day × 24 hour)
3. Generate manifest.json (git_commit, holdout_wape_score, ...)
4. Залить оба файла на платформу
5. Получить WAPE_score от платформы
6. Записать в ledger

**Hard rules:**
- R1 clinerule 23: filename = unique (submission_<model_id>_<date>_<ts>.csv)
- R2 clinerule 23: manifest.json рядом с CSV
- R4 hackathon-rules: no LLM > 4B, no synthetic data
- R6 hackathon-rules: training ≤ 60 min, inference ≤ 2 sec

## Полный workflow

### Шаг 1: Train модель

```bash
uv --directory ml run python scripts/train_xgboost.py \
    --model-id xgboost_v8_poi \
    --start-date 2025-01-01 --end-date 2025-08-31 \
    --holdout-start 2025-09-01 --holdout-end 2025-10-31
```

**Holdout WAPE-score** (последняя строка output):
```
Holdout WAPE-score (сен–окт, calibrated): 0.8751 (Δ +0.0070)
```

Записать в WORK_LOG: `model_id, train_range, holdout_score`.

### Шаг 2: Generate submission БЕЗ --output

**❌ НЕПРАВИЛЬНО (F-039):**
```bash
uv run python scripts/make_submission.py \
    --model-id xgboost_v8_poi \
    --output predictions/submission.csv
```

**✅ ПРАВИЛЬНО (clinerule 23 R1):**
```bash
uv run python scripts/make_submission.py \
    --model-id xgboost_v8_poi \
    --submission-id v8-poi
# → predictions/submission_xgboost_v8_poi_20251101_20251231_<run_ts>.csv
# → predictions/submission_xgboost_v8_poi_20251101_20251231_<run_ts>.json
```

**Что создаётся:**
- CSV с прогнозами (14640 строк, 3 колонки: route, date, hour, prediction)
- manifest.json рядом (R2)
- `predictions/submission.csv` = alias, **не source-of-truth** (R3)

### Шаг 3: Sanity-check (clinerule 28 R3)

```bash
# 1. Файл существует и не пустой
ls -la predictions/submission_xgboost_v8_poi_*.{csv,json}

# 2. CSV валидный (14640 строк)
wc -l predictions/submission_xgboost_v8_poi_*.csv  # 14641 с header

# 3. Header: route;date;hour;prediction
head -1 predictions/submission_xgboost_v8_poi_*.csv

# 4. Manifest содержит holdout_wape_score
cat predictions/submission_xgboost_v8_poi_*.json | python3 -m json.tool | grep holdout

# 5. Compare with best_so_far
python3 -c "
import json, glob
best = max(
    float(json.load(open(m))['holdout_wape_score'])
    for m in sorted(glob.glob('predictions/submission_*.json'))
    if 'holdout_wape_score' in json.load(open(m))
)
current = json.load(open('predictions/submission_xgboost_v8_poi_*.json'))['holdout_wape_score']
print(f'Best so far: {best:.4f}, Current: {current:.4f}')
"

# 6. Optional: make submission-verify
make submission-verify CSV=predictions/submission_xgboost_v8_poi_*.csv
```

### Шаг 4: Залить на платформу

Платформа хакатона (зависит от конкретного):
- Web form: drag-and-drop CSV
- API: POST multipart/form-data

**Что заливать:**
- `predictions/submission_xgboost_v8_poi_*.csv` — обязательно
- `predictions/submission_xgboost_v8_poi_*.json` — если принимает

**Подождать** 1-5 минут (асинхронный счёт).

### Шаг 5: Получить score и записать в ledger

В `docs/ledger/findings.jsonl`:
```json
{
  "id": "F-NNN",
  "ts": "<ISO timestamp UTC>",
  "title": "Submission #<N> (<submission_id>) — local <X> / platform <Y>",
  "context": "Залили predictions/<unique_name>.csv. Drift = <Y-X>pp",
  "evidence": "<csv_path>, <manifest_path>",
  "impact": "<лучше/хуже best_so_far>, <drift cause>",
  "tickets": ["T-XXX"],
  "tags": ["submission", "platform-result", "<drift|loss|win>"],
  "links": [...]
}
```

**Затем обновить manifest:**
```python
m['platform_submitted'] = True
m['platform_score'] = <WAPE_score>
m['platform_score_submitted_at'] = '<ISO timestamp>'
```

### Шаг 6: Обновить best_so_far

```bash
make handoff-update  # если улучшение — обновит STATUS.md
```

### Шаг 7: Коммит (если улучшение)

```bash
git add predictions/<unique_name>.csv predictions/<unique_name>.json
git commit -m "feat(ml): submission #<N> <submission_id> — WAPE_score=<platform> (best)"
```

## Local vs Platform drift (F-040)

**Часто:** local holdout > platform (drift -0.1-0.2pp).

**Почему:**
- Holdout сент-окт = продолжение train (мало drift)
- Submission ноя-дек = drift (event-venue, holidays, погода)
- Bias calibration overfit (in-sample)
- POI/anomaly фичи статичны — не объясняют динамику ноября

**Что делать:**
- Holdout ≥ X% выше цели (если цель 0.85 → ждать ≥ 0.92)
- Записывать drift в F-NNN после каждой заливки

## Anti-patterns

❌ **Заливать без sanity-check**: битый CSV, нет holdout → трата слота
❌ **`--output predictions/submission.csv`**: не уникальное имя (F-039)
❌ **Не записать F-NNN после заливки**: нельзя восстановить хронологию
❌ **Заливать с holdout_score < best_so_far**: пустая трата попытки
❌ **Игнорировать drift**: теряем возможность понять что не работает

## Acceptance criteria

```markdown
- [ ] Модель обучена, holdout_score записан
- [ ] Submission сгенерирован БЕЗ --output (уникальное имя)
- [ ] Sanity-check 5 критериев пройден
- [ ] CSV + manifest залиты на платформу
- [ ] F-NNN в ledger с local + platform scores + drift
- [ ] Если улучшение: best_so_far обновлён в STATUS.md
```

## Cross-references

- clinerule 23 — submission versioning (R1-R5)
- clinerule 27 — WAPE vs WAPE-score
- clinerule 28 — submission workflow (5 sanity checks)
- F-039 — bug с --output predictions/submission.csv
- F-040 — local vs platform drift
- ml/scripts/make_submission.py — entry point
- ai/skills/03-submission-pipeline.md — старый skill по submission v1

