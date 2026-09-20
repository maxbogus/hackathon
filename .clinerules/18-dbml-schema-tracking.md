# 18-dbml-schema-tracking.md — DB schema как код

## Что это

DBML (Database Markup Language) — declarative schema description для PostgreSQL.
**Source of truth = SQLAlchemy ORM в `apps/backend/app/models/`** (когда появится).
DBML — **генерируется**, не редактируется.

**Цели:**
1. Документация схемы БД без ручного труда (одна команда → свежая ERD)
2. CI gate против schema drift (забыли alembic migration, забыли модель)
3. Privacy annotations: `PII / cat-3 PII / opaque blob` — извлекаются из module docstring
4. Визуализация: paste `schema.dbml` в https://dbdiagram.io → ERD картинка

**Источник шаблона:** candidate-tracker/docs/architecture/ + scripts/generate_dbml.py

## Артефакты (генерируются)

```
docs/architecture/
├── schema.dbml              # DBML для https://dbdiagram.io
├── schema-tables.md         # human-readable таблица всех моделей + privacy hints
└── .gitkeep                 # папка живёт в git (артефакты — тоже)
```

**Commit policy:** оба файла `.dbml` и `schema-tables.md` коммитятся в git.
Они маленькие (<10KB) и нужны для ревью PR.

## Команды Makefile

```bash
make arch-dbml            # регенерировать schema.dbml + schema-tables.md
make arch-dbml-check      # CI gate: exit 1 если drift
make arch-dbml-init       # создать docs/architecture/.gitkeep + .dbml/.md skeleton
```

## Как добавить новую модель (TDD flow)

1. Создать файл `apps/backend/app/models/stop.py`:
   ```python
   """Stop — остановка трамвая.

   Privacy: no-PII (public transport infrastructure).
   """
   from sqlalchemy.orm import Mapped, mapped_column
   from app.core.db import Base

   class Stop(Base):
       __tablename__ = "stops"
       id: Mapped[int] = mapped_column(primary_key=True)
       name: Mapped[str]
       lat: Mapped[float]
       lon: Mapped[float]
   ```
2. Создать alembic migration (`make alembic-revision MSG="add stops"`)
3. `make arch-dbml` — проверить что новая таблица появилась в `schema.dbml`
4. Commit всё вместе (model + migration + schema.dbml + schema-tables.md)

## Privacy hints (из docstring)

Конвенция — первая строка docstring модели описывает purpose, далее `Privacy: <hints>`.
Генератор парсит регуляркой `Privacy:\s*(.+)$`:

| Hint | Что значит |
|---|---|
| `PII` | Персональные данные (ФЗ-152). Шифровать at-rest. |
| `cat-3 PII` | Особо чувствительные (паспорт, медданные). Отдельный vault. |
| `opaque blob` | Бинарные данные (PDF, фото). Не индексировать. |
| `no-PII` | Публичные/инфраструктурные данные. |

Это попадает в `schema-tables.md` колонку `Privacy hints` — облегчает аудит 152-ФЗ.

## Когда запускать

| Событие | Триггер |
|---|---|
| Добавил/изменил SQLAlchemy модель | `make arch-dbml` |
| CI (на каждый push) | pre-commit hook `make arch-dbml-check` |
| Презентация | открыть `.dbml` в dbdiagram.io, скриншот ERD |
| Новый разработчик в команде | показать `schema-tables.md` — это ground truth |

## Структура `schema.dbml`

```dbml
// Schema generated from apps/backend/app/models (SQLAlchemy).
// Update models and run: make arch-dbml
// Visualize at https://dbdiagram.io

Project transit_ai {
  database_type: 'PostgreSQL'
  Note: 'Transit-AI — пассажиропоток трамваев Москвы'
}

Table stops {
  id int [pk, not null]
  name varchar [not null]
  lat float [not null]
  lon float [not null]
  Note: 'Остановка трамвая (public infrastructure).'
}

Table routes { ... }
Table predictions { ... }   // timeseries, TimescaleDB hypertable
Table models { ... }        // реестр обученных ML-моделей
// ...
```

## Структура `schema-tables.md`

```markdown
| Table | Model | Purpose | Privacy hints | Columns |
|-------|-------|---------|---------------|---------|
| `users` | `User` | Диспетчеры и админы | PII | 5 |
| `stops` | `Stop` | Остановки трамвая | no-PII | 8 |
| `routes` | `Route` | Маршруты | no-PII | 6 |
| `predictions` | `Prediction` | Прогнозы пассажиропотока | no-PII | 12 |
| `ml_models` | `MLModel` | Реестр обученных моделей | no-PII | 9 |
```

## Подводные камни

1. **Пустая папка `models/`** → скрипт работает с warning, schema.dbml содержит
   "no models registered yet" (TODO: первая модель — T-038+).
2. **`Base` не импортирован** → `Base.metadata` пустой, все модели пропущены.
3. **Циклические импорты в моделях** → alembic env.py должен загружать `app.models`
   целиком (см. candidate-tracker/apps/backend/alembic/env.py).
4. **TimescaleDB hypertable** → DBML не знает про hypertable, добавляем Note вручную
   в сгенерированный `.dbml` (комментарий).

## Не делать

- ❌ Редактировать `schema.dbml` руками (edit models → regenerate)
- ❌ Использовать DBML как runtime schema (это документация, а не миграция)
- ❌ Путать `arch-dbml` (generate) с `alembic upgrade head` (apply migration)
- ❌ Коммитить SQL dump базы (это `.gitignore`)
