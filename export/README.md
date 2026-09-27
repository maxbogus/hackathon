# export/ — сдаточный пакет Transit-AI

> Что это: самодостаточная выжимка артефактов для формы «Загрузка решения» хакатона
> Московского транспорта (трек «ИИ-прогноз загрузки трамвайных маршрутов»).
> Собрано: 2026-09-27. Проверка: `sh verification/verify_install.sh`.

## Соответствие 6 пунктам формы → папки

| # | Пункт формы | Папка | Главное внутри |
|---|---|---|---|
| 1 | Артефакты ML + код обучения/инференса, README | `01-ml/` | `artifacts/` (model.pkl + meta.json), `artifacts_index.md`, `submissions/` (лучший CSV + manifest), `reports/` |
| 2 | Внешние данные + инструкция проверки | `02-external-data/` | `raw/`, `normalized/` + `manifest.json` (sha256), `../04-architecture/EXTERNAL_DATA.md` |
| 3 | Запускаемый веб-сервис (Docker), точки входа | `03-service/` | `docker-compose.yml`, `endpoints.md`, `api/openapi.json` |
| 4 | Схема архитектуры и модулей, область определения/адаптации | `04-architecture/` | `architecture.svg`, `dfd_ru.svg|png`, `schema.dbml`, `schema-tables.md`, `MODEL_DOMAIN.md` |
| 5 | Производительность (замеры) + доп. возможности | `05-performance/` | методика + цифры, `load_profiles.md` |
| 6 | Ограничения и план развития (в т.ч. отложенные задачи) | `06-limitations-roadmap/` | `LIMITATIONS` = `BUSINESS_VALUE.md`, `BACKLOG.md` (RICE) |
| — | Готовый текст формы | `README_form.md` | 6 полей, RU, со ссылками |
| — | Проверка установки/запуска | `verification/` | `verify_install.sh`, `verification-report.txt` |

```
export/04-architecture/
├── erd.svg          # ERD из schema.dbml (dbml-renderer) — открывается в браузере
├── erd.png          # ERD в PNG (schema.dbml → dot → graphviz `dot -Tpng`)
├── erd.dot          # промежуточный Graphviz DOT (для своих стилей)
├── schema.dbml      # source of truth (генерируется из SQLAlchemy: make arch-dbml)
└── schema-tables.md # таблица таблиц + privacy hints
```

## Как пересобрать схему БД и ERD

```bash
make arch-dbml                                     # SQLAlchemy → docs/architecture/schema.dbml
dbml-renderer -i docs/architecture/schema.dbml -f svg -o docs/architecture/schema_erd.svg
dbml-renderer -i docs/architecture/schema.dbml -f dot -o /tmp/erd.dot
dot -Tpng -Gdpi=140 /tmp/erd.dot -o docs/architecture/schema_erd.png
```

Требуется глобальный CLI `dbml-renderer` (`npm install -g @softwaretechnik/dbml-renderer`)
и Graphviz (`dot`). Альтернатива без установки — вставить `schema.dbml` на https://dbdiagram.io.

## Быстрый старт для жюри

```bash
# 1) проверка окружения + запуск + smoke (без нагрузки)
sh export/verification/verify_install.sh

# 2) вручную
make up                                   # docker compose: postgres, redis, backend, frontend, workers
make external-gen && make external-verify  # JSON из внешних источников + sha256 (offline)
curl -s localhost:8000/api/v1/healthz      # {"status":"ok"}
open http://localhost:5173                 # дашборд (Диспетчер / Аналитик / Исторические данные)
open http://localhost:8000/docs            # Swagger UI
```

## Ключевые факты (одной таблицей)

| Показатель | Значение |
|---|---|
| Лучший платформенный WAPE-score | **0.83455** (полоса 0.80–0.88 → 8/10) |
| Локальный holdout WAPE-score | 0.8751 (train 01.01–31.08.2025, holdout 09–10.2025) |
| Submission | 10 маршрутов × 61 день × 24 часа = **14 640 строк** |
| p95 инференса (k6 smoke, 10 VU × 30 s) | **26.3 мс** (SLA ≤ 2000 мс), 0 % ошибок, 300 запросов |
| Внешние источники | 5 (погода, трафик, календарь РФ, POI, события) + 8 нормализованных артефактов с sha256 |
| API | 31 путь, 13 тегов (`03-service/endpoints.md`) |
| Модели | baseline_v1, xgboost_v8_poi, xgboost_v9_events (+ CatBoost-бленд) |

## Как пересобрать пакет

```bash
make external-gen        # обновить normalized JSON + manifest.json
python3 scripts/generate_dbml.py   # schema.dbml + schema-tables.md (или make arch-dbml)
mmdc -i docs/submission/diagrams/dfd_ru.mmd -o export/04-architecture/dfd_ru.png -b white -s 2
make export-verify       # обязательные файлы + sha256 (см. checksums.sha256)
```

## Известные пробелы (добить при наличии времени)

- [x] **ERD-картинка** (`erd.svg` / `erd.png`) — собрана через
      `dbml-renderer` (@softwaretechnik/dbml-renderer) + Graphviz; см. раздел выше.
- [ ] **10 слайдов питча**: в репозитории только `slide_01_pain_points.md`.
- [ ] **k6 HTML/JSON-отчёты**: в headless Docker не сохраняются (F-111) — в
      `05-performance/` приложен консольный summary.
- [ ] **Postman-коллекция** из `openapi.json` (генератор `scripts/gen_api_docs.py` — в плане).
- [ ] **Docker-образы .tar** (`dist/`) для офлайн-запуска без сборки; ml-pipeline ≈13.8 ГБ
      (близко к лимиту ТЗ 15 ГБ) — см. ограничения.
- [ ] **`SUBMISSION.pdf`** через `pandoc` (доступен локально).

## Ограничения пакета

- Датасет организаторов (`data/real`, ~10 ГБ) в пакет **не входит** — поставляется хакатоном.
- `export/01-ml/artifacts/` — только выбранные модели (baseline_v1, xgboost_v8_poi, xgboost_v9_events);
  полный список sweep-артефактов остался в `ml/artifacts/` (гитигнор).
