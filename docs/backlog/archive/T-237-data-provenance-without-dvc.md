---
id: T-237
phase: 7
title: Data provenance without DVC and portable export package
priority: P1
effort: 3
unit: hours
rice:
  R: 4
  I: 2
  C: 0.8
  score: 2.13
depends_on: [T-236]
blocks: []
tags: [delivery, data, docs]
status: done
created: 2026-09-28
updated: 2026-09-28
assignee: ""
---

## Context

Подготовка репозитория к передаче внешней комиссии (продолжение T-236). Три дефекта,
из-за которых пакет выглядел полнее, чем был на самом деле:

1. **DVC без remote.** `.dvc/config` содержал только `no_scm` + локальный `cache dir`;
   3 committed `*.dvc` (`data/real/train.csv.dvc`, `test.csv.dvc`,
   `data/external/normalized/manifest.json.dvc`) обещали provenance, которого у получателя
   нет: `dvc pull` падал. Параллельно бинарники уже едут через git-lfs (D-046) — два
   механизма на одну задачу. Плюс 24 untracked `ml/artifacts/*/model.pkl.dvc` внутри
   gitignored каталога (нулевая ценность, 0 байт экономии — hardlink).
2. **Обещанная, но несуществующая команда.** `export/README.md` в разделе «Как пересобрать
   пакет» давал `make export-verify`, но цели в Makefile не было, а
   `export/checksums.sha256` (63 записи) никто не проверял (F-147).
3. **Непереносимые метаданные.** `data/external/normalized/*.json` писались с абсолютным
   путём входа (`str(p)`), поэтому в git попал `/home/maxbogus/...`, а при прогоне из
   контейнера — `/app/...`: те же файлы у получателя лежат по другому пути, плюс git
   «шумит» при каждом прогоне через контейнер (F-148).

## Acceptance Criteria

- [x] DVC удалён целиком: 27 `*.dvc`, `.dvc/`, `mlops/dvc-cache`, `mlops/probes/dvc_probe.sh`,
      `mlops/tests/test_dvc_probe.py`, цели `dvc-*` и `mlops-probe`, упоминания в `.gitignore`
- [x] `make export-verify` существует и проверяет обязательные файлы + sha256
      (`scripts/verify_export.py`); есть `make export-checksums` для регенерации
- [x] `verification/verification-report.txt` исключён из checksums (пересоздаётся при verify)
- [x] Пути входов в коммитимых артефактах относительные (RED→GREEN:
      `test_input_paths_are_repo_relative`), `data/external/normalized/*` перегенерированы
- [x] Документация синхронизирована: `export/README.md`, `mlops/README.md`,
      `mlops/MLOPS_LAB.md`, `.clinerules/33-mlops-lab.md`, `docs/MLFLOW.md`

## Technical Notes

- Provenance после T-237: `docs/lineage/datasets/*.json` (sha256 датасета в git),
  `data/external/normalized/manifest.json` (sha256 каждого источника),
  `export/checksums.sha256` (`make export-verify`), git-lfs для бинарных артефактов.
- `repo_root_from_output()` определяет корень по конвенции `<root>/data/external/normalized`,
  затем по маркеру `pyproject.toml`; иначе путь остаётся абсолютным (безопасный fallback).
- DVC-цифры в `mlops/MLOPS_LAB.md` помечены как исторические — отчёт пилота не переписываем.

## Verification

```bash
make export-verify                 # OK: 14 обязательных файлов, 62 хэша
make export-checksums              # перегенерация после правок пакета
uv run --directory apps/harvester pytest tests/ -q --no-cov   # 23 passed
make mlops-test                    # 18 passed / 2 skipped
make external-verify               # 8 источников: sha256 + rows_count + schema
git grep -l '/home/maxbogus' -- data/external/normalized/      # пусто
```

## Status

`done` (2026-09-28). Результаты:

| Проверка | Результат |
|---|---|
| DVC-артефакты | 0 `*.dvc`, нет `.dvc/`, нет `mlops/dvc-cache`, цели удалены |
| `make export-verify` | `OK: обязательные файлы на месте (14), sha256 сверено (62)` |
| Пути в normalized | `data/external/...` (относительные), `external-verify` проходит |
| harvester tests | 23 passed (было 22 + новый тест переносимости) |
| mlops tests | 18 passed / 2 skipped (было 20/2 — минус 2 DVC-теста) |

Находки и решение: F-147 (обещанный `export-verify`), F-148 (абсолютные пути в артефактах), D-051.
