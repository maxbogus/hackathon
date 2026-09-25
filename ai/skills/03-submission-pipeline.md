# Skill: submission-pipeline — генерация и параметризация submission

**Когда подключать:** при работе над любым T-NNN, который генерит или
использует `predictions/submission.csv` (T-145, T-147, T-148+, T-152).

## Зачем этот скилл

Submission на платформу хакатона — это **артефакт с тройкой**
`(date-range, model-version, run-timestamp)` + обязательный manifest.

Если работаешь с submission и не знаешь как сейчас устроено именование
или где брать manifest — **прочитай этот скилл целиком**.
Не пытайся "просто перегенерить submission.csv" — F-021 уже зафиксировал
почему это плохо.

## Анатомия submission (R1-R5 из clinerule 23)

```
predictions/
├── submission_route_baseline_v1_20251101_20251231_20260925T184512Z.csv  ← прогон #2
├── submission_route_baseline_v1_20251101_20251231_20260925T184512Z.json  ← manifest #2
├── submission.csv                                                          ← alias последнего
└── submission_route_baseline_v1.csv                                        ← LEGACY (F-021)
```

Манифест — JSON, см. полную схему в `.clinerules/23-submission-versioning.md`.
Обязательные поля: `submission_id`, `csv_filename`, `git_commit`,
`dataset_hash_sha256`, `model_id`, `train_date_range`, `submission_date_range`,
`row_count`, `expected_rows`, `coefficients`, `holdout_wape_score`.

## Сценарий 1: Сгенерить новый submission

```bash
# 1. Убедиться что модель обучена
make train-route-baseline

# 2. Сгенерить submission с человеко-читаемым id
make submission SUBMISSION_ID=v2-bias-calibration \
                 COEF_WEATHER=1.0 \
                 COEF_EVENT=1.0 \
                 COEF_SEASON=1.0

# 3. Verify (R4)
make submission-verify CSV=predictions/submission_route_baseline_v1_*.csv

# 4. Зрительно проверить что manifest.json рядом
ls predictions/*v2-bias*

# 5. Залить на платформу
#    (платформа хакатона — браузер/curl, не автоматизируется)
# 6. Обновить manifest: platform_score, platform_submitted=true
# 7. Закоммить CSV + manifest + изм. в backend (если был)
git add predictions/ docs/ledger/findings.jsonl
git commit -m "feat(ml): submission v2-bias-calibration (T-147)

Holdout WAPE-score=0.8751 (+0.007 vs uncalibrated)
Platform score: 0.XXXXX (залить вручную, обновить manifest)
Refs: T-147, F-021"
```

## Сценарий 2: "Какой именно submission я заливал вчера?"

```bash
# Быстрый поиск
for f in predictions/*.json; do
  python3 -c "
import json
d = json.load(open("$f"))
sub = d.get("platform_submitted", False)
if sub:
    print("$f: platform_score=%s, git=%s, model=%s" % (
        d["platform_score"], d["git_commit"], d["model_id"]))
" 2>/dev/null
done

# Или find по git_commit
for f in predictions/*.json; do
  python3 -c "import json; d=json.load(open("$f")); print(d["git_commit"], d["csv_filename"])" 2>/dev/null
done | grep "e64ff08"
```

Если manifest нет — это и есть проблема F-021. **Не гадай** какой CSV был
залит — попроси пользователя посмотреть историю браузера / корзину платформы,
или просто регенерируй с manifest и считай это baseline.

## Сценарий 3: Revert на предыдущий submission

```bash
# Посмотреть какие версии есть
ls -lt predictions/*.csv

# Восстановить старый manifest → train та же модель → rerun
git log --oneline -- predictions/
# Найти коммит, где был залит целевой submission
# git checkout <commit> -- predictions/<old>.csv
# или просто скопировать
cp predictions/submission_..._<commit-ts>.csv predictions/submission.csv
```

## Сценарий 4: Добавить новый параметр (напр. coef_holiday)

Когда в `make_submission.py` нужно прокинуть новый коэффициент:

1. **Опиши параметр в clinerule 23** — какой дефолт, как попадает в manifest.
2. **Добавь в argparse** скрипта (`--coef-holiday`, default=1.0).
3. **Пробрось в `manifest["coefficients"]["holiday"]`**.
4. **Пробрось в `preds *= coef_holiday`** рядом с существующими.
5. **Обнови существующие manifest** если coef=1.0 дефолтный (опционально).
6. **Тест**: `make submission-verify` после прогона.

## Сценарий 5: Добавить новый model (напр. xgboost_v2)

1. Обучить: `make train-xgboost-v2` → создаст `ml/artifacts/xgboost_v2/`.
2. Сгенерить submission:
   `make submission MODEL_ID=xgboost_v2 SUBMISSION_ID=v3-xgboost-initial`
3. Verify автоматически подтянет `ml/artifacts/xgboost_v2/meta.json`:
   - `model_id`, `trained_at`, `git_commit`, `train_data_hash`, `metrics`
4. Platform submit.
5. В manifest должны появиться **обязательные поля**, см. R2 clinerule 23.

## Частые ошибки (F-021 disambig)

| Симптом | Причина | Что делать |
|---|---|---|
| `predictions/submission.csv` без `.json` рядом | Старый прогон до введения правила | Удалить или перегенерировать через `make submission SUBMISSION_ID=...` |
| `submission_<model>_<ts>.csv` без даты в имени | Старый формат до R1 | Удалить, перегенерировать |
| Разные CSV утверждают что они "submission #1" | Нет submission_id | Добавить `--submission-id` при следующем прогоне |
| Manifest говорит `platform_score=0.72568`, но это был не тот CSV | Забыли обновить manifest | Всегда обновлять manifest сразу после заливки (commit atomic) |

## Код, который нужно написать (T-NNN, планируется)

### `ml/transit_ai/submission/manifest.py`

```python
"""submission_manifest.json writer/validator (T-148a)."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], text=True
    ).strip()

def dataset_hash(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]

def write_manifest(
    out_dir: Path,
    csv_filename: str,
    model_id: str,
    model_uri: str,
    train_range: tuple[str, str],
    sub_range: tuple[str, str],
    row_count: int,
    expected_rows: int,
    total_predictions: float,
    coefficients: dict[str, float],
    post_processing: list[str],
    holdout_wape_score: float | None = None,
    submission_id: str | None = None,
) -> Path:
    manifest = {
        "submission_id": submission_id or model_id,
        "csv_filename": csv_filename,
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "git_branch": subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip(),
        "data_source": "RealSource",
        "dataset_hash_sha256": "pending",  # populate via dataset_hash()
        "model_id": model_id,
        "model_uri": model_uri,
        "train_date_range": list(train_range),
        "submission_date_range": list(sub_range),
        "row_count": row_count,
        "expected_rows": expected_rows,
        "total_predictions_sum": total_predictions,
        "coefficients": coefficients,
        "post_processing": post_processing,
        "platform_submitted": False,
        "platform_score": None,
        "platform_score_submitted_at": None,
        "holdout_wape_score": holdout_wape_score,
    }
    out = out_dir / csv_filename.replace(".csv", ".json")
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return out
```

### `ml/tests/test_submission_manifest.py` (RED phase, T-148a)

```python
"""Tests for submission manifest."""
from pathlib import Path
from transit_ai.submission.manifest import write_manifest

def test_manifest_writes_json(tmp_path: Path):
    csv_filename = "submission_x_v1_20251101_20251231_20260925T1845Z.csv"
    write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1820456.32,
        coefficients={"weather": 1.0, "event": 1.0, "season": 1.0},
        post_processing=["clip_negatives"],
        holdout_wape_score=0.8751,
        submission_id="v2",
    )
    expected_json = tmp_path / "submission_x_v1_20251101_20251231_20260925T1845Z.json"
    assert expected_json.exists()
    import json
    d = json.loads(expected_json.read_text())
    assert d["submission_id"] == "v2"
    assert d["model_id"] == "x_v1"
    assert d["row_count"] == 14640
    assert d["expected_rows"] == 14640
    # R1: csv_filename должен содержать все 3 id (date_start, date_end, run_ts)
    for token in ("_20251101_", "_20251231_", "T1845Z.csv"):
        assert token in d["csv_filename"], f"missing token {token}"
```

## Cross-references

- **Clinerule 23**: `.clinerules/23-submission-versioning.md` — hard rules R1-R5
- **Finding F-021**: в `docs/ledger/findings.jsonl` — почему правило появилось
- **Текущий код**: `ml/scripts/make_submission.py` — что нужно расширить
- **Makefile targets**: `submission`, `submission-verify`, `submission-clean`
- **TDD**: при добавлении параметров — начать с теста `test_make_submission.py`
