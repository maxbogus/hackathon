# HACKATHON_CHECKLIST — Transit-AI submission readiness

> Финальный чек-лист перед сабмитом 03.10.2026.
> Создано в рамках T-137 (P0, RICE 6.0).
> Для каждого пункта — статус (✅/⚠️/❌) + ссылка на доказательство + команда проверки.

**Условные обозначения:**

- ✅ — done, есть доказательство
- ⚠️ — частично / требует внимания перед submission
- ❌ — не сделано / требует работы

---

## Секция 1. Презентация (R10)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| 10 слайдов, 5 мин | ⚠️ | `docs/hackathon/presentation/` (см. T-133) | `ls docs/hackathon/presentation/ | wc -l` |
| Структура (pain→solution→demo→tech→results→team) | ⚠️ | slide_01..slide_10 | `ls docs/hackathon/presentation/slide_*.md` |

**Команды:**

```bash
ls docs/hackathon/presentation/   # должно быть >=10 .md
```

---

## Секция 2. Видео демо (R10)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| Запись экрана 2-3 мин | ❌ | `docs/hackathon/presentation/demo_video.mp4` (отсутствует) | `ls -la docs/hackathon/presentation/demo_video.mp4` |
| Сценарий: dispatcher → passenger → alerts → карта | ⚠️ | планируется в следующей сессии | _см. HANDOFF.md_ |

**Команды:**

```bash
# Записать через OBS / загрузить на YouTube (unlisted)
file docs/hackathon/presentation/demo_video.mp4
```

---

## Секция 3. Repository hygiene

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| README.md обновлён | ✅ | `README.md` — обзор, команды, бейджи | `head -50 README.md` |
| README на русском (T-115) | ⚠️ | T-115 в backlog, ready | `make backlog-ready` |
| LICENSE (MIT) | ⚠️ | отсутствует файл в корне | `ls LICENSE` |
| .gitignore исключает .env, ml/artifacts/, predictions/, data/ | ✅ | `.gitignore` (зафиксировано в Phase 0) | `grep -E '^\.env$|^ml/artifacts/$|^predictions/$|^data/$' .gitignore` |

**Команды:**

```bash
test -f LICENSE && echo "LICENSE OK"
test -f README.md && echo "README OK"
grep -E '^\.env$|^ml/artifacts/$|^predictions/$|^data/$' .gitignore
```

---

## Секция 4. Контракты

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| OpenAPI свежий | ✅ | `make api-gen` без изменений | `make api-gen` |
| Orval синхронизирован | ✅ | `apps/frontend/src/generated/api.ts` | `make fe-gen` |
| JSON Schema артефактов | ✅ | `docs/schemas/prediction_artifact.schema.json` | `cat docs/schemas/prediction_artifact.schema.json` |

**Команды:**

```bash
make api-gen && git status docs/api/openapi.json
make fe-gen && git status apps/frontend/src/generated/
```

---

## Секция 5. Метрики (R8)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| Validation report | ✅ | `make inventory` -> `data/validation_reports/inventory.json` | `make inventory` |
| Model metrics (baseline_v1) | ✅ | `make evaluate` -> `reports/baseline_v1_metrics.json` | `make evaluate` |
| Model metrics (xgboost_v1) | ✅ | `reports/xgboost_v1_metrics.json` | `ls reports/xgboost_v1_metrics.json` |
| WAPE-score на реальных данных | ✅ | T-144 — `ml/transit_ai/reports/metrics.py:wape_score` | `uv run python -c "from ml.transit_ai.reports.metrics import wape_score; print('OK')"` |

**Команды:**

```bash
make inventory && ls data/validation_reports/inventory.json
make evaluate && ls reports/*_metrics.json
```

---

## Секция 6. Anti-fraud (R5 + R3)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| meta.json содержит git_commit | ✅ | `ml/transit_ai/training/registry.py` | `cat ml/artifacts/baseline_v1/meta.json | jq .git_commit` |
| meta.json содержит train_data_hash | ✅ | sha256 датасета при обучении | `cat ml/artifacts/baseline_v1/meta.json | jq .train_data_hash` |
| meta.json содержит seed | ✅ | seed зафиксирован (R3 reproducible) | `cat ml/artifacts/baseline_v1/meta.json | jq .seed` |
| timestamps (start, end) | ✅ | ISO timestamps | `cat ml/artifacts/baseline_v1/meta.json | jq '.timestamps'` |

**Команды:**

```bash
for m in ml/artifacts/*/meta.json; do
  echo "=== $m ==="
  jq '{model_id, git_commit, train_data_hash, seed, timestamps}' "$m"
done
```

---

## Секция 7. Лицензия (R1)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| Код под MIT | ⚠️ | LICENSE файл отсутствует в корне | `ls LICENSE` |
| Все зависимости — open-source | ✅ | uv.lock (MIT/BSD/Apache) | `uv run pip-licenses --format=markdown` |

**Команды:**

```bash
test -f LICENSE && head -3 LICENSE
# Если нет — создать: https://opensource.org/licenses/MIT
```

---

## Секция 8. Reproducibility (R3)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| uv.lock закоммичен | ✅ | `uv.lock` в git | `git ls-files uv.lock` |
| yarn.lock закоммичен | ✅ | `apps/frontend/yarn.lock` в git | `git ls-files apps/frontend/yarn.lock` |
| Random seed зафиксирован | ✅ | seed=42 в скриптах обучения | `grep -rn 'seed.*=.*42' ml/transit_ai/` |
| Docker образ <= 15 GB | ✅ | multi-stage + pinned image (T-164) | `docker images transit-ai-backend --format "{{.Size}}"` |

**Команды:**

```bash
test -f uv.lock && echo "uv.lock OK"
test -f apps/frontend/yarn.lock && echo "yarn.lock OK"
grep -rn 'random.seed|torch.manual_seed|np.random.seed' ml/transit_ai/training/
```

---

## Секция 9. No internet at runtime (R4)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| Backend не делает HTTP к внешним сервисам | ✅ | grep по `apps/backend/` | `grep -rE 'httpx|requests' apps/backend/app/ | grep -v localhost` |
| ML pipeline не делает HTTP | ✅ | grep по `ml/transit_ai/` | `grep -rE 'httpx|requests' ml/transit_ai/ | grep -v localhost` |
| Исключение: наш backend (localhost:8000) | ✅ | tools ассистента | `grep -rE 'localhost:8000' apps/assistant/` |

**Команды:**

```bash
grep -rE 'httpx|requests|aiohttp.ClientSession' apps/ ml/transit_ai/ | grep -v 'localhost' | grep -v '__pycache__'
```

---

## Секция 10. Real data only (R5)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| Синтетика только в dev/test | ✅ | `SyntheticSource` помечен для тестов | `grep -rn 'SyntheticSource' ml/transit_ai/` |
| Real data — основной pipeline | ✅ | T-143 — `ml/transit_ai/data/real.py` | `cat ml/transit_ai/data/real.py | head -30` |
| Submission на реальных данных | ✅ | T-145 — `predictions/submission.csv` | `head -5 predictions/submission.csv` |

**Команды:**

```bash
grep -l 'SyntheticSource' ml/transit_ai/ -r
ls predictions/submission.csv
head -3 predictions/submission.csv
```

---

## Секция 11. Time limits (R6)

| Требование | Статус | Доказательство | Команда проверки |
|---|---|---|---|
| Суммарное обучение <= 60 мин | ✅ | T-165 — `scripts/check_training_time.py` | `uv run python scripts/check_training_time.py` |
| Makefile target `check-training-time` | ✅ | встроен в CI gate | `make check-training-time` |
| Inference <= 2 сек (SLA) | ✅ | T-161 — `scripts/check_load_sla.py` | `make loadtest-check` |
| Обучение вне Docker | ✅ | D-001 в ledger | `grep -rE 'FROM.*nvidia' apps/backend/Dockerfile` (должно быть пусто) |

**Команды:**

```bash
uv run python scripts/check_training_time.py
make check-training-time
make loadtest-smoke && make loadtest-check
```

---

## Секция 12. SLA Compliance (R6) — _T-167_

_(T-167 добавит эту секцию со ссылками на docs/load-profiles/reports/)_

---

## Секция 13. Container Resources (R3) — _T-167_

_(T-167 добавит таблицу resource limits всех сервисов)_

---

## Секция 14. Load Testing Methodology — _T-167_

_(T-167 добавит таблицу 5 профилей k6)_

---

## Как использовать

1. **Перед сабмитом:** пройти все секции, проставить статус.
2. **Любой ⚠️/❌ — блокер** для submission.
3. **Секции 12-14:** добавляются в T-167.

## Cross-references

- T-137 — этот чек-лист (P0, RICE 6.0)
- T-167 — секции 12-14 (P1, RICE 6.0, depends_on T-137+T-161)
- T-160..T-166 — load testing + SLA infrastructure
- `.clinerules/05-hackathon-rules.md` — R1..R10 hard rules
- `.clinerules/22-load-testing.md` — load testing methodology
