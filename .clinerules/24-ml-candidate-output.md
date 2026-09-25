# 24-ml-candidate-output.md — SUBMISSION CANDIDATE после каждого ML запуска

## Зачем

T-148a закрыл **manifest.json** (R1-R5 clinerule 23), но пользователь всё ещё
должен **сам** сравнивать кандидатов и решать что заливать. Это источник ошибок
(F-021: пользователь запутался, какой из 2 CSV был залит).

**Решение:** после каждого ML скрипта (который генерит или обновляет submission)
выводить блок `SUBMISSION CANDIDATE` со всей нужной информацией для решения
"заливать или нет".

## Hard Rules

### R1. Каждый ML-скрипт выводит блок после успешного завершения

Скрипты которые ОБЯЗАНЫ выводить блок:
- `make_submission.py` — после write_manifest()
- `train_xgboost.py` — после save_model()
- `calibrate.py` — после apply calibration
- (будущее) `train_gru.py`, `train_hybrid.py` — после save_model()

### R2. Формат блока (строгий, парсится регуляркой)

```
============================================================
SUBMISSION CANDIDATE
============================================================
CSV:           <абсолютный путь к CSV>
Manifest:      <абсолютный путь к manifest.json>
Model:         <model_id>
Submission ID: <submission_id>
Holdout WAPE:  <float, 4 знака>
Date range:    <YYYY-MM-DD> → <YYYY-MM-DD>
Rows:          <int>
Total preds:   <float, .0f форматирование>
Recommendation: <READY_TO_UPLOAD | NEEDS_FIX | WORSE_THAN_PREVIOUS | IDENTICAL_TO_PREVIOUS>
Platform prev: <WAPE или "none">
============================================================
```

### R3. Recommendation enum

| Значение | Когда выводить |
|---|---|
| `READY_TO_UPLOAD` | holdout лучше предыдущего platform score ИЛИ нет previous |
| `NEEDS_FIX` | row_count != expected_rows ИЛИ manifest verify failed |
| `WORSE_THAN_PREVIOUS` | holdout хуже предыдущего (delta < -0.005) |
| `IDENTICAL_TO_PREVIOUS` | holdout равен предыдущему с точностью 0.001 (negative result) |

Threshold для "лучше/хуже" = **0.005** (0.5pp). Это шумовой порог — меньший
delta не считается значимым изменением.

### R4. Сравнение с предыдущим submission

Helper `print_candidate()` читает предыдущий manifest из `predictions/*.json`
(выбирает самый новый с `platform_submitted=true`) и сравнивает holdout_wape_score.

Если предыдущего нет — `Platform prev: none`, `Recommendation: READY_TO_UPLOAD`.

### R5. Не блокировать вывод

Блок выводится через `print()` ВСЕГДА, даже если `print_candidate()` упал
с exception (try/except вокруг всего кроме print самого блока).

## Где применяется

| Файл | Где в коде |
|---|---|
| `ml/transit_ai/submission/candidate.py` | новый модуль с `print_candidate()` |
| `ml/scripts/make_submission.py` | после write_manifest() |
| `ml/scripts/train_xgboost.py` | после save_model() (T-152) |
| `ml/scripts/calibrate.py` | после apply calibration |

## Реализация (skill 04)

См. `ai/skills/04-ml-candidate-output.md` — полная реализация helper'а
с типизированными аргументами, enum'ом Recommendation, и тестами.

## Don't do

- ❌ Не выводить блок в формате, который нельзя распарсить регуляркой
- ❌ Не использовать `print(...)` с другим текстом между строками блока
  (парсеры ищут точные заголовки `CSV:`, `Manifest:`, etc.)
- ❌ Не выводить относительные пути (всегда абсолютные)
- ❌ Не подавлять блок даже при ошибках (R5)

## Cross-references

- Clinerule 23: `.clinerules/23-submission-versioning.md` — manifest.json R1-R5
- Skill 03: `ai/skills/03-submission-pipeline.md` — submission-pipeline
- Skill 04: `ai/skills/04-ml-candidate-output.md` — реализация helper'а
- T-148a: clinerule 23 в коде
- T-149: этот тикет
- F-021: оригинальная находка
