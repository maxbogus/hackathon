# Distribution Workflow для жюри (T-198b)

Этот документ описывает как готовый стенд Transit-AI передаётся от организаторов
к жюри через **.tar архив + Яндекс.Диск**.

> **TL;DR для жюри:** скачать .tar → `make import-images TAR=...` → `make up` → `make up-status`

---

## Архитектура стенда

```
┌──────────────────────────────────────────────────────────────────┐
│  host machine (Linux/Mac/WSL2)                                   │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌────────┐ │
│  │  postgres   │  │   redis     │  │   backend    │  │frontend│ │
│  │  :5432      │  │   :6379     │  │   :8000      │  │  :5173 │ │
│  │  timescale  │  │   cache+    │  │   FastAPI    │  │  nginx │ │
│  │  +actuals+  │  │   Celery    │  │   alembic +  │  │  Vite  │ │
│  │  +predictions│ │   broker    │  │   seed +     │  │  SPA   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └───┬────┘ │
│         │                │                │              │      │
│         └──── transit-net (Docker network) ─────────────┘      │
│                       │                                          │
│              ┌────────┴────────┐                                 │
│              │                 │                                 │
│      ┌───────┴──────┐  ┌───────┴───────┐                         │
│      │  harvester   │  │  ml-pipeline  │                         │
│      │  Celery      │  │  Celery       │                         │
│      │  worker      │  │  worker       │                         │
│      │  (data/)     │  │  (train +     │                         │
│      │              │  │   predict)    │                         │
│      └──────────────┘  └───────────────┘                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Volumes (на хосте):
  ./data/               # CSVs от организаторов хакатона (8 GB train + 2 GB test)
  ./ml/artifacts/       # обученные модели (XGBoost, baseline, ...)
  ./predictions/        # submission.csv + manifests
```

## Что внутри

### Backend services (через backend/seed_predictions.py)

| Таблица | Строк | Источник |
|---|---|---|
| `actuals` | 68801 | `data/real/train.csv` + `data/real/test.csv` (НГПТ валидации) |
| `predictions` | 14640 | `data/real/test_submission.csv` (эталон, route 5 = 0) |
| `feature_toggles` | 6 | alembic seed (T-174) |
| `zero_overrides` | 4 | alembic seed (F-051, F-060) |
| `prediction_runs` | (пусто) | для логов Celery ml-pipeline |

### Frontend (5 экранов)

| URL | Назначение |
|---|---|
| `/` | Главная — выбор роли (диспетчер/пассажир/аналитик/планировщик) |
| `/passenger` | **Пассажирский** интерфейс — ближайшие рейсы, рекомендации когда ехать |
| `/dispatcher` | **Диспетчерский** интерфейс — алерты перегруженных остановок, ETA |
| `/analyst` | **Аналитический** дашборд — графики прогноз vs факт, WAPE-score, CSV export |
| `/planner` | **Планировщик** сценариев — Monte Carlo "что если" (заглушка) |

### ML pipeline (Celery, apps/ml_pipeline)

| Task | Что делает |
|---|---|
| `ml_pipeline.train_xgboost` | Обучает XGBoost на train.csv (WAPE-score=0.875 baseline) |
| `ml_pipeline.predict_window` | Генерит predictions на date range |
| `ml_pipeline.full_pipeline` | train + predict последовательно |

Триггер через `make pipeline-full` (на хосте) или `POST /api/v1/pipeline/full` (UI).

---

## Workflow для организаторов

### Шаг 1: Pre-build wheels на машине с интернетом

```bash
# Генерирует apps/{backend,harvester,ml_pipeline}/wheels/ (~430 MB total)
make build-all

# Проверить что wheels готовы:
du -sh apps/*/wheels/
# 180M    apps/backend/wheels/
# 50M     apps/harvester/wheels/
# 200M    apps/ml_pipeline/wheels/
```

### Шаг 2: Собрать Docker images (offline через wheels)

```bash
# Docker build использует pip install --no-index (НЕ ходит в PyPI)
make up

# Проверка:
make up-status
# ✓ Backend healthz: 200
# ✓ Backend readyz: 200
# ✓ Frontend: 200
# ✓ {"has_predictions": true, "predictions_count": 14640, ...}
```

### Шаг 3: Export всех images в .tar

```bash
# Создаёт dist/transit-ai-stack-YYYYMMDD-HHMM.tar (~1.5 GB)
make export-images

# Проверить:
ls -lah dist/
# -rw-r--r-- 1 root root 1.5G ... transit-ai-stack-20260927-1530.tar
```

### Шаг 4: Залить на Яндекс.Диск

**Через web-интерфейс:**
1. Открыть https://disk.yandex.ru/
2. Создать папку `Hackathon/TransitAI/`
3. Перетащить `dist/transit-ai-stack-*.tar` в эту папку
4. ПКМ → "Поделиться" → "Создать публичную ссылку"
5. Скопировать ссылку

**Через yadisk CLI** (быстрее для больших файлов):
```bash
pip install yadisk  # или uv tool install yadisk

# Авторизация: https://oauth.yandex.ru/authorize\?response_type\=token\&client_id\=...
export YADISK_TOKEN=<oauth_token>
yadisk upload dist/transit-ai-stack-*.tar "/Hackathon/TransitAI/"

# Получить публичную ссылку:
yadisk publish "/Hackathon/TransitAI/transit-ai-stack-*.tar"
# → https://disk.yandex.ru/d/XXXXX
```

### Шаг 5: Передать ссылку жюри

- Email / Telegram / в день проверки
- Сообщить версию (timestamp в имени .tar)

---

## Workflow для жюри

### Шаг 1: Скачать .tar

**Через web:**
1. Открыть ссылку от организаторов
2. Скачать `transit-ai-stack-YYYYMMDD-HHMM.tar` (~1.5 GB, ~5-10 мин)

**Через CLI:**
```bash
wget "https://disk.yandex.ru/d/XXXXX/transit-ai-stack-YYYYMMDD-HHMM.tar"
```

### Шаг 2: Загрузить images в локальный Docker

```bash
# Из корня репозитория:
make import-images TAR=~/Downloads/transit-ai-stack-YYYYMMDD-HHMM.tar

# Ожидаемый вывод:
# ✓ Images загружены.
# → Следующий шаг: make up
```

### Шаг 3: Поднять стек

```bash
make up

# Стек поднимается за 30-60 сек (alembic + seed).
# Backend healthcheck срабатывает через ~90 сек.
```

### Шаг 4: Проверить что всё работает

```bash
make up-status
```

**Ожидаемый вывод:**
```
=== Stack health ===
Backend healthz:  200
Backend readyz:   200
Frontend:         200
Backend /api/v1/predictions/status:
{
  "has_predictions": true,
  "predictions_count": 14640,
  "actuals_count": 68801,
  "model_ids": ["test_submission_baseline"],
  "running_pipeline": false
}

=== Container status ===
SERVICE      STATUS             PORTS
backend      Up X minutes        8000/tcp
frontend     Up X minutes        0.0.0.0:5173->80/tcp
postgres     Up X minutes (healthy)
redis        Up X minutes (healthy)
harvester    Up X minutes
ml-pipeline  Up X minutes
```

### Шаг 5: Открыть UI

```
http://localhost:5173
```

**Проверить все 5 экранов:**
- `/` → выбор роли
- `/passenger` → рекомендации для пассажиров
- `/dispatcher` → алерты
- `/analyst` → графики прогнозов (главный экран для оценки)
- `/planner` → сценарии "что если"

### Шаг 6 (опционально): Запустить свежий ML pipeline

```bash
# Обучает XGBoost + генерит predictions (~5-10 мин на CPU)
make pipeline-full

# Проверить что predictions обновились:
curl http://localhost:8000/api/v1/predictions/status
# → model_ids: ["test_submission_baseline", "xgboost_v_..."]
```

---

## Troubleshooting

### `make import-images` падает с "permission denied"

```bash
# Docker требует root или membership в docker group
sudo make import-images TAR=...

# Или добавить себя в группу:
sudo usermod -aG docker $USER
# Перелогиниться.
```

### Port 5173/5432/6379/8000 already in use

```bash
# Остановить старые контейнеры
docker compose down

# Или найти процессы, занимающие порты:
sudo lsof -i :5173
sudo kill -9 <PID>
```

### Backend не отвечает (healthcheck DOWN после 90 сек)

```bash
# Смотреть логи backend
docker compose logs backend --tail=50

# Типичные проблемы:
# 1. PostgreSQL не стартовал — проверить docker compose logs postgres
# 2. Seed скрипт упал — там будет ошибка чтения CSV
# 3. .venv не собрался — uv sync --offline failed (проверить что wheels на месте)
```

### Predictions count = 0 (seed не отработал)

```bash
# Войти в backend контейнер
docker compose exec backend /bin/bash

# Попробовать seed вручную
cd /app/apps/backend
uv run --offline python -m app.scripts.seed_predictions --data-dir /app/data

# Проверить что data смонтирован:
ls -la /app/data/
# Должно быть train.csv, test.csv, test_submission.csv
```

### Frontend не загружается (502 Bad Gateway)

```bash
# nginx не может достучаться до backend.
# Проверить что оба в одной сети:
docker compose ps

# Проверить nginx.conf (должен быть upstream backend:8000):
docker compose exec frontend cat /etc/nginx/conf.d/app.conf
```

---

## Размеры артефактов

| Артефакт | Размер |
|---|---|
| `apps/backend/wheels/` (на хосте) | ~180 MB |
| `apps/harvester/wheels/` | ~50 MB |
| `apps/ml_pipeline/wheels/` | ~200 MB |
| **wheels итого** | **~430 MB** |
| Docker image `transit-ai-backend` | ~350 MB |
| Docker image `transit-ai-frontend` | ~150 MB |
| Docker image `transit-ai-harvester` | ~200 MB |
| Docker image `transit-ai-ml-pipeline` | ~700 MB |
| **images итого** | **~1.4 GB** |
| `dist/transit-ai-stack-*.tar` (со всеми images) | **~1.5 GB** |
| Данные `data/real/` (train + test) | **~10 GB** (НЕ включаются в .tar) |

> ⚠️ **Важно:** `data/` НЕ включается в .tar архив. Данные должны быть на
> хосте проверяющего (поставляются отдельно организаторами хакатона).
> Если data отсутствует — backend стартует, но predictions будут пустыми.

---

## Что оценивается жюри

**R10 (hackathon-rules):** 10 слайдов, 5 минут презентация.

**Что показывать:**
1. **/analyst** — главный экран, графики прогнозов (WAPE-score baseline)
2. **Свежий прогноз** — `make pipeline-full` показывает работу ML pipeline
3. **CSV export** — `/api/v1/predictions/export.csv` (7583+ строк)
4. **EmptyPredictions + Run now** — UI показывает fallback если predictions нет

**Метрики:**
- WAPE-score ≥ 0.85 (цель жюри, см. docs/HACKATHON_CHECKLIST.md)
- Inference latency < 2 сек (R6 SLA)
- Все 3 endpoint возвращают данные

См. также: [docs/HACKATHON_CHECKLIST.md](HACKATHON_CHECKLIST.md), [.clinerules/27-wape-score-vs-wape.md](../.clinerules/27-wape-score-vs-wape.md).
