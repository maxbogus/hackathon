---
id: T-137
phase: 7
title: docs/HACKATHON_CHECKLIST.md — заполнить R8 hackathon-rules перед сабмитом 03.10
priority: P0
effort: 2
unit: hours
rice:
  R: 4
  I: 3.0
  C: 1.0
  score: 6.0
depends_on: []
blocks: []
tags: [docs, hackathon, submission, r8, mandatory, beneficiary]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim,svetlana"
---

# T-137: docs/HACKATHON_CHECKLIST.md — заполнить R8 hackathon-rules перед сабмитом

## Context

R8 hackathon-rules (`.clinerules/05-hackathon-rules.md`):
> «Перед сабмитом на хакатоне:
>  1. Запустить `make inventory` → `data/validation_reports/inventory.json`
>  2. Запустить `make evaluate` → `reports/<model>_metrics.json`
>  3. Заполнить `docs/HACKATHON_CHECKLIST.md`»

**Текущее состояние:**
- `docs/HACKATHON_CHECKLIST.md` **не существует** (подтверждено `ls`).
- `README.md` ссылается на него: `docs/HACKATHON_CHECKLIST.md — чек-лист дня X`.
- Все 3 ссылки в README на этот файл — **битые** (broken).
- Без чек-листа нельзя сабмитить (R8 нарушен → дисквалификация).

## Acceptance Criteria

- [ ] Создан `docs/HACKATHON_CHECKLIST.md` с секциями:
  - [ ] **Презентация** (R10): 10 слайдов, 5 мин
  - [ ] **Видео демо**: 2-3 мин, запись экрана
  - [ ] **Repository hygiene**: README.md (T-115), LICENSE, .gitignore
  - [ ] **Контракты**: OpenAPI свежий, Orval синхронизирован
  - [ ] **Метрики**: `data/validation_reports/inventory.json`, `reports/<model>_metrics.json`
  - [ ] **Anti-fraud** (R5 + R3): meta.json с git_commit, train_data_hash, seed
  - [ ] **Лицензия** (R1): код под Apache 2.0 / MIT / BSD
  - [ ] **Reproducibility** (R3): uv.lock и yarn.lock закоммичены
  - [ ] **No internet at runtime** (R4): grep по apps/ и ml/ — нет HTTP к внешним сервисам
  - [ ] **Real data only** (R5): синтетика только в dev/test
  - [ ] **Time limits** (R6): суммарное обучение ≤ 60 мин
  - [ ] **Code review** (R9): каждый PR проверен
- [ ] Для каждого пункта — ссылка на доказательство
- [ ] Для каждого пункта — статус: ✅ / ⚠️ / ❌
- [ ] Ссылка на чек-лист добавлена в README.md (заменяет битую)
- [ ] Закоммичен Conventional Commit: `docs(hackathon): add submission checklist (T-137)`

## Technical Notes

Структура `docs/HACKATHON_CHECKLIST.md`:
```markdown
# HACKATHON_CHECKLIST — Transit-AI submission readiness
> Финальный чек-лист перед сабмитом 03.10.2026.

## Секция 1. Презентация (R10)
- [ ] Слайды: docs/hackathon/presentation/slide_01_pain_points.md + ещё 9 слайдов
- [ ] Длительность: 5 мин

## Секция 2. Видео демо
- [ ] Видео записано: docs/hackathon/presentation/demo_video.mp4

## Секция 3. Repository hygiene
- [ ] README.md обновлён (T-115)
- [ ] LICENSE (MIT) в корне
- [ ] .gitignore исключает: .env, ml/artifacts/, predictions/, data/

## Секция 4. Контракты
- [ ] make api-gen — без изменений
- [ ] make fe-gen — без изменений

## Секция 5. Метрики
- [ ] data/validation_reports/inventory.json (make inventory)
- [ ] reports/baseline_v1_metrics.json (make evaluate)
- [ ] reports/xgboost_v1_metrics.json

## Секция 6. Anti-fraud
- [ ] meta.json содержат: git_commit, train_data_hash, seed, timestamps

## Секция 7. Лицензия
- [ ] LICENSE: MIT

## Секция 8. Reproducibility
- [ ] uv.lock закоммичен
- [ ] yarn.lock закоммичен

## Секция 9. No internet at runtime
- [ ] grep -r "httpx\|requests" apps/ ml/transit_ai/ | grep -v localhost
- [ ] Только Open-Meteo (T-123, optional)

## Секция 10. Time limits
- [ ] Суммарное обучение ≤ 60 мин: docs/reports/training_time.md

## Секция 11. Code review
- [ ] Каждый merged PR имеет approve
- [ ] Conventional Commits enforced
```

## Verification

```bash
# 1. Файл существует
test -s docs/HACKATHON_CHECKLIST.md && echo OK

# 2. README ссылка работает
grep "HACKATHON_CHECKLIST.md" README.md

# 3. Все секции присутствуют
grep -c "^## Секция" docs/HACKATHON_CHECKLIST.md

# 4. R8.1: validation report
make inventory
ls data/validation_reports/inventory.json

# 5. R8.2: model metrics
make evaluate
ls reports/*_metrics.json
```

## Beneficiary Impact

**Команда (⭐⭐⭐⭐⭐)** — без чек-листа можно забыть критичные требования и провалить аудит.
**Жюри (⭐⭐⭐⭐)** — чек-лист = проявление серьёзности подхода.

RICE: 6.0 — топ-5 приоритет. Без этого тикета нельзя сабмитить.
