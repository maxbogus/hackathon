# 28-submission-workflow-local-vs-platform.md — submission workflow с проверкой drift

## Проблема

Платформа хакатона возвращает **другой WAPE_score** чем локальный holdout.
Submission #8 (T-168 POI): local 0.8751 → platform 0.73231 = drift -0.143pp.
Submission #3 (F-024): local 0.8976 → platform 0.14734 = drift ОГРОМНЫЙ.

Хотя drift непредсказуем, можно:
1. **Минимизировать** риск неправильной заливки (R1 clinerule 23)
2. **Зафиксировать** local vs platform для каждого submission в ledger
3. **Предупредить** что holdout ≠ platform (F-040, обновление clinerule 27)

## Hard Rules

### R1. Submission filename = unique (clinerule 23)

**НЕ указывать `--output predictions/submission.csv`** — ломает уникальность.
Без `--output` скрипт создаёт:
```
submission_<model_id>_<start_date>_<end_date>_<run_ts>.csv
submission_<model_id>_<start_date>_<end_date>_<run_ts>.json
```

См. clinerule 23 + F-039.

### R2. Заливать ОБА файла: CSV + manifest.json

Платформе нужны оба файла рядом (R2 clinerule 23):
- `<unique_name>.csv` — данные прогноза
- `<unique_name>.json` — manifest с `holdout_wape_score`, `git_commit`, ...

Если платформа требует **только CSV** — manifest всё равно должен существовать
рядом для traceability (R5 clinerule 23: `make submission-verify`).

### R3. Перед заливкой — sanity-check 5 критериев

```bash
# 1. Файл существует и не пустой
ls -la predictions/submission_<unique>.csv

# 2. Manifest существует рядом
ls -la predictions/submission_<unique>.json

# 3. CSV валидный: 14640 строк, 3 колонки, route;date;hour;prediction
head -3 predictions/submission_<unique>.csv
wc -l predictions/submission_<unique>.csv

# 4. Holdout WAPE-score ≥ best_so_far (если нет — зачем заливать?)
python3 -c "
import json
m = json.load(open('predictions/submission_<unique>.json'))
print(f'Holdout: {m[\"holdout_wape_score\"]:.4f}')
print(f'Best so far: <from ledger>')
"

# 5. CSV не равен alias predictions/submission.csv (должен быть уникальным)
[ "$(md5sum predictions/submission.csv | cut -d' ' -f1)" != \
  "$(md5sum predictions/submission_<unique>.csv | cut -d' ' -f1)" ] \
  || echo "WARNING: identical to submission.csv alias"
```

### R4. После заливки — обновить ledger

В `docs/ledger/findings.jsonl` создать F-NNN:
```json
{
  "id": "F-NNN",
  "title": "Submission #<N> (<submission_id>) на платформе — WAPE_score=<local>/<platform>",
  "context": "...",
  "evidence": "<ссылка на manifest + лог платформы>",
  "impact": "drift = <platform> - <holdout> = <drift>pp"
}
```

**Какие поля обязательны:**
- `holdout_wape_score` (из manifest)
- `platform_score` (от платформы, обновить после заливки)
- `drift = platform_score - holdout_wape_score`
- `tickets: ["T-XXX"]`
- `links: [<csv_path>, <json_path>]`

## Workflow заливки

```
1. Train модель (make train-xgboost или uv run scripts/train_xgboost.py)
2. Submission pipeline: uv run scripts/make_submission.py --model-id <id> \
        --submission-id <tag>     # НЕ --output!
3. SANITY: проверить 5 критериев (R3)
4. Залить CSV на платформу + manifest.json (если требуется)
5. Подождать score (обычно 1-5 минут)
6. F-NNN в ledger
7. Если WAPE_score ≥ best_so_far → отметить submission как new best
8. Если WAPE_score ухудшился → откатить на previous best
```

## Типичные ошибки (анти-паттерны)

❌ **`--output predictions/submission.csv`** → не уникальное имя (F-039)
❌ **Залить только CSV** без manifest → нет traceability
❌ **Залить submission с holdout < best_so_far** → трата слота
❌ **Не записать F-NNN после заливки** → нельзя восстановить что залито
❌ **Игнорировать платформенный score < holdout** → упустить причину drift
❌ **Залить alias `submission.csv`** → не знаешь что платформа реально посчитала

## Когда НЕ заливать submission

- Holdout WAPE_score **ниже** best_so_far (не улучшает)
- Holdout > 0.99 (подозрительно, может быть утечка данных)
- Файл не прошёл sanity-check (R3)
- Не записали F-NNN с local holdout
- Submission period изменился (новые holidays не в calendar)

## Cross-references

- clinerule 23 — submission versioning (R1-R5)
- clinerule 27 — WAPE vs WAPE-score (как читать метрики)
- F-039 — bug с --output predictions/submission.csv
- F-040 — local vs platform drift
- F-032, F-030 — последние успешные submission'ы
- ml/scripts/make_submission.py — entry point
- ai/skills/07-hackathon-platform-workflow.md — длинная инструкция
