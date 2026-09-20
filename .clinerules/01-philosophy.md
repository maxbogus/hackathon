# 01-philosophy.md — Принципы проекта

## 1. Contract-first

Сначала **контракт** (JSON Schema артефакта, OpenAPI эндпоинта, Pydantic-схема запроса).
Потом — реализация. Потом — данные.

Почему: на хакатоне **нет данных заранее**. Без контракта каждый новый источник
ломает 80% кода. С контрактом — только адаптер.

## 2. Data-agnostic

Все источники за интерфейсом `DataSource` (`ml/transit_ai/data/base.py`).
Реализации:
- `SyntheticSource` — генерит правдоподобные данные (bbox Москвы, ~800 остановок, 40 маршрутов, 2 года)
- `RealSource` — на хакатоне, читает parquet/csv/json от организаторов

Замена = 1 час работы, 1 файл, 0 изменений в API.

## 3. ML вне Docker

Обучение моделей **скриптами** в `ml/` через `make train-*`.
Артефакты на диск в `ml/artifacts/<model_id>/`:
```
ml/artifacts/baseline_v1/
├── meta.json          # модель, метрики, гиперпараметры, дата
├── model.pkl          # или .pt / .onnx
├── preprocessor.pkl   # scaler, encoder
└── calibration.json   # per-bucket biases
```

API читает файлы по контракту через `apps/backend/forecast/loader.py`.

Почему не в Docker:
- Docker инвалидирует GPU-доступ для ML
- Артефакты на диске проще версионировать (через meta.json)
- Переключение модели = atomic rename в `ml/artifacts/active/`
- ML развивается независимо от API

## 4. MVP first, RICE > 5 next

Сначала **минимально жизнеспособный** продукт:
- `BaselineMean` + 1 endpoint + карта = 2 дня работы
- Потом — `XGBoost` + графики = +1 день
- Потом — `GRU` + калибровка = +1 день
- Потом — `Hybrid` + Monte Carlo = +1 день

Жюри оценивает **работающее демо**, не сложность моделей.

## 5. Knowledge capture (ledger)

Каждое значимое решение (RICE > 5) → `docs/ledger/decisions.jsonl`.
Каждая находка → `docs/ledger/findings.jsonl`.
Находка может стать → note → rule → skill (см. `15-promote-finding.md`).

Зачем: **не переучивать агента** в каждой сессии. Решения накапливаются,
можно искать по тегам и использовать для презентации.

## 6. TDD: RED → GREEN → REFACTOR

Каждый тикет начинается с **падающего теста**.
Нет теста = нет кода (исключение: документация, конфиги).

## 7. Conventional Commits

`<type>(<scope>): <subject>` — обязательно (enforced `commit-msg` hook).

Зачем:
- Автогенерация CHANGELOG
- Понятная история (видно что менялось: ml/, backend/, frontend/)
- Можно фильтровать `git log --grep="feat(ml):"`
