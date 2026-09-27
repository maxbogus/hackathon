# SUBMISSION — Transit-AI (форма «Загрузка решения»)

> Готовые тексты для 6 обязательных полей формы хакатона. Заполняется ссылками;
> `⟨…⟩` — подставить перед отправкой. Версия: 2026-09-27.

## 1. Артефакты ML-модели, код обучения/инференса, README

**Ссылка:** ⟨https://github.com/maxbogus/hackathon⟩ · ⟨Яндекс.Диск: `ml-artifacts.zip` (XGBoost/CatBoost/baseline + `meta.json`)⟩

Модель: gradient boosting (XGBoost + CatBoost-бленд) по всем 10 маршрутам трамваев Москвы;
признаки — календарь/сезонность, погода (Open-Meteo), POI/инфраструктура (OSM),
события, лаги и per-route статистики; постобработка — per-route bias-калибровка,
кап/зануление ночных часов, праздничные множители. Инференс читает артефакты по
контракту `docs/schemas/prediction_artifact.schema.json`.

Запуск: `make install && make up && make external-gen && make train-xgboost && make submission`.
Анти-фрод (R3/R5): каждый `meta.json` содержит `git_commit`, `train_data_hash` (sha256),
`seed`, времена обучения; датасет не коммитится, манифест нормализации — в git.

## 2. Внешние данные (трафик, погода, календарь, прочее)

**Ссылка:** ⟨https://github.com/maxbogus/hackathon/tree/master/data/external⟩ + `docs/submission/EXTERNAL_DATA.md`

| Источник | Ссылка/способ получения | Эффект на платформе |
|---|---|---|
| Погода — Open-Meteo Historical | URL запроса в `EXTERNAL_DATA.md` (без ключа, CC-BY) | включена; в пределах шума |
| Дорожный трафик — OSM Overpass | запрос Overpass (ODbL) в `EXTERNAL_DATA.md` | выключен (на holdout хуже) |
| Календарь РФ/Москвы: праздники, переносы, каникулы | lib `holidays==0.55` + производственный календарь + myschool.moscow | **подтверждённый лифт** |
| POI (146 объектов, 13 категорий) | OSM Overpass + ручная разметка | **подтверждённый лифт** |
| События (открытия/ремонты) | офлайн-дамп KudaGo/Wikipedia | нейтрально после бленда |

Пайплайн: `make external-gen` → `data/external/normalized/*.json` + `manifest.json`
(sha256), `make external-verify` (схема + хэши + строки). `validators_lookup.csv`
честно помечен как производный признак от `train.csv`.

## 3. Запускаемый веб-сервис (Docker Compose), точки входа, инструкция

**Ссылка:** ⟨https://github.com/maxbogus/hackathon⟩ + `docs/DISTRIBUTION.md`

```bash
git clone ⟨repo⟩ && cd hackathon
cp .env.example .env            # плейсхолдеры, ключи не нужны для демо
make up                         # postgres+redis+backend+frontend+workers
```
Точки входа: UI `http://localhost:5173` · Swagger `http://localhost:8000/docs` ·
`/api/v1/healthz` · `/api/v1/predictions/load` · `/api/v1/predictions/db/{route}` ·
`/api/v1/historical/load` · `/api/v1/geo/routes` · `/api/v1/predictions/export.csv|xlsx`.
Экраны: Диспетчер (карта Москвы + карточки загрузки), Аналитик (графики, тогглы
корректирующих коэффициентов, CSV/XLSX), Исторические данные (таблица).

## 4. Схема архитектуры и модулей; область определения/адаптации

**Ссылка:** `docs/architecture/architecture.svg`, `docs/submission/diagrams/dfd_ru.svg`, `docs/MODEL_DOMAIN.md`

Поток: внешние источники → **шаг 0 ETL** (`apps/harvester/app/build`, normalized + sha256)
→ ML-признаки → XGBoost-артефакт → FastAPI → дашборд. Область определения: 10 маршрутов
(1, 5, 7, 11, 12, 17, 25, 26, 28, 50) × часы; train 01.01–31.08.2025, holdout 09–10.2025,
сабмит 11–12.2025. Пределы: нет новых городов/маршрутов без ≥2 мес. истории, нет
real-time инцидентов, нет погодных аномалий. Адаптация: инструкции «новый маршрут /
новый период / новый город / новый источник» — в `MODEL_DOMAIN.md`.

## 5. Производительность (замеры) и дополнительные возможности

**Ссылка:** README §«Производительность», `docs/load-profiles/reports/*.html`

k6 0.54 в Docker (cpuset 0–1), эндпоинт `GET /api/v1/predictions/stop/{id}`:
smoke 10 VU × 30 s → 300 запросов, **0 % ошибок, p95 = 26 мс** (SLA ≤ 2000 мс, запас ~75×),
avg 7.7 мс. Лимиты экземпляра: backend 0.5 vCPU / 768 MiB, postgres 512 MiB, redis 128 MiB,
frontend 128 MiB. Воспроизведение: `make loadtest-smoke`, `make loadtest-baseline`,
`make loadtest-check`.

Дополнительно: ETL внешних данных с sha256-манифестом; управление feature-тоглами и
корректирующими коэффициентами из UI с мгновенным пересчётом; наборы прогнозов
«активный/эталон» с откатом; MCP-сервер (stdio) и LLM-ассистент (LiteLLM-паттерн);
экспорт CSV + XLSX; карта маршрутов с цветовой шкалой загрузки.

## 6. Ограничения решения и план развития

**Ссылка:** `docs/BUSINESS_VALUE.md`, `docs/submission/EXTERNAL_DATA.md`

Ограничения: drift local↔platform (−0.04…−0.14 п.п.); до 16.12.2025 маршрут 5 не работал
(cold start, зануляется); ночные часы и выходные предсказываются хуже (±40 %); аварии/
перекрытия/погодные аномалии не учитываются; инференс батчевый (не стриминговый);
`validators` — производный признак. Лучший платформенный результат: **WAPE-score 0.83455**
(полоса 0.80–0.88 → 8/10 по критерию 1).

Развитие: P1 — Kafka-стрим, Яндекс.Пробки live, новые города, Optuna; P2 — Bayesian
uncertainty, MLflow + A/B; P3 — симулятор расписания сети, оптимизация выбросов.

## Ссылки-проверки перед отправкой

- [ ] README открывается, раздел «Производительность» на месте
- [ ] `data/external/normalized/manifest.json` в репозитории (sha256 артефактов)
- [ ] `make up` + `curl localhost:8000/api/v1/healthz` → `{"status":"ok"}` на чистой машине
- [ ] Лучший submission залит: `predictions/submission_route_baseline_v1_20251101_20251231_20260926T171106Z.csv` (platform 0.83455)
