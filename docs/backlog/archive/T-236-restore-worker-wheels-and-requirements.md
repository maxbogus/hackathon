---
id: T-236
phase: 0
title: Restore worker wheels and requirements, rebuild images
priority: P0
effort: 3
unit: hours
rice:
  R: 4
  I: 3
  C: 0.9
  score: 3.6
depends_on: []
blocks: [T-237, T-238, T-239]
tags: [mlops, docker, delivery]
status: done
created: 2026-09-28
updated: 2026-09-28
assignee: ""
---

## Context

Пилот T-235 (F-132) вскрыл, что `apps/*/wheels` и `apps/*/requirements.txt` уехали
в `docs/apps/**` (6.7 ГБ): `docs/apps/backend/wheels` 3.2 ГБ, `docs/apps/ml_pipeline/`
3.2 ГБ, `docs/apps/frontend` 342 МБ. Каталог игнорируется git-правилом `wheels/`
(`.gitignore:29`), но лежит в `docs/` и выглядит как второй набор приложений.

Следствия для передачи внешней комиссии:
1. `export/verification/verify_install.sh` §2 проверяет именно
   `apps/{backend,harvester,ml_pipeline}/wheels` → сейчас WARN × 3, offline-сборка
   образов без сети невозможна.
2. Образы воркеров не пересобрать → приходилось держать костыль
   `make pipeline-worker-dev` (bind-mount + `pip install pyyaml`), что в поставке
   выглядит как незавершённость.
3. Пустой огрызок `apps/ml-pipeline/` (дефис) рядом с `apps/ml_pipeline/` —
   про него предупреждает тот же verify-скрипт (§2, строка 60).

## Acceptance Criteria

- [x] `apps/{backend,harvester,ml_pipeline}/wheels` + `requirements.txt` восстановлены
      из **текущего** `uv.lock` (не копией из `docs/apps/*`: там снапшот до T-235,
      без `pyyaml` — F-133)
- [x] Образы `backend`, `harvester`, `ml-pipeline` собираются offline
      (`docker build --network=none` → exit 0)
- [x] Связка Airflow → Celery → ML проверена без dev-воркера
- [x] Цели `pipeline-worker-dev` / `pipeline-worker-dev-stop` удалены (Makefile + `.PHONY`)
- [x] Dev bind-mount `./apps/ml_pipeline/app` в `docker-compose.yml` удалён (F-145)
- [x] `apps/ml-pipeline/` удалён
- [x] `docs/apps/` удалён (освобождено 6.7 ГБ), в репозитории не осталось второго
      набора приложений (F-146)
- [x] `sh export/verification/verify_install.sh --quick` → `FAIL=0` / `VERIFIED`

## Technical Notes

- Регенерация: `make build-all` (`uv export --frozen` + `pip download --only-binary=:all:`),
  нужен одноразовый сетевой доступ. Это dev-инструмент, R4 (no internet at runtime) не нарушен.
- `wheels/` и `requirements.txt` не обязаны попадать в git (правило `wheels/` в `.gitignore`);
  комиссия получает готовые образы `.tar` (`docs/DISTRIBUTION.md`), поэтому §2
  verify-скрипта при сборке из исходников остаётся WARN, а не FAIL. Если решим иначе —
  дописать явно в `docs/DISTRIBUTION.md`.
- Отчётный размер `~430 MB` в сообщении `build-all` устарел (backend тянет torch/CUDA) —
  обновить по факту `du -sh apps/*/wheels`.

## Verification

```bash
make build-all
docker compose build backend harvester ml-pipeline
sh export/verification/verify_install.sh --quick
du -sh docs/apps 2>/dev/null || echo "docs/apps удалён"
```

## Status

`done` (2026-09-28). Результаты:

| Проверка | Результат |
|---|---|
| `make build-all` из текущего lock | wheels backend 3.2 G / harvester 5.7 M / ml_pipeline 3.2 G |
| `docker build --network=none` (harvester) | `exit=0` — offline-сборка подтверждена |
| `make up` | все сервисы up, backend `healthy`, frontend `200` |
| Код в контейнере vs репозиторий | `md5 tasks.py` совпал; зарегистрированы 4 задачи `ml_pipeline.*`; `pyyaml 6.0.3` |
| ML-путь через брокер | `run_ml_script(lineage_snapshot)` → `SUCCESS` за 26.8 с (sha256 `e4157ed7…`) |
| Airflow-путь | `airflow tasks test transit_pipeline harvest` → `SUCCESS` (weather 365 / traffic 41 / poi 146 / events 8) |
| `verify_install.sh --quick` | `FAIL=0 WARN=1` (k6 пропущен флагом) → **VERIFIED** |

Находки и решение: F-143 (yarn/PnP), F-144 (лишний `uv` = сетевой шаг), F-145 (dev-mount
кода воркера), F-146 (6.7 ГБ `docs/apps` + дубль `apps/ml-pipeline`), D-050.
