# Отложенные задачи (backlog на после хакатона)

Источник: `docs/backlog/tickets/*.md` (YAML frontmatter + RICE). Отсортировано по RICE.

| RICE | ID | Заголовок | Приоритет | Часы | Статус |
|---|---|---|---|---|---|
| 10.0 | T-217 | Fix 422 regression on /historical/{id} and /insights/alerts | P0 | 3 | done |
| 10.0 | T-149 | clinerule 24 + skill 04 - SUBMISSION CANDIDATE block после каждого ML  | P0 | 1 | in-progress |
| 10.0 | T-148a | make_submission.py соответствие clinerule 23 — manifest.json + --submi | P0 | 1 | done |
| 10.0 | T-144 | WAPE-score в ml/transit_ai/reports/metrics.py (primary metric хакатона | P0 | 1 | done |
| 10.0 | T-115 | README — добавить English version, исправить ссылки, отдельный раздел  | P0 | 1 | ready |
| 9.6 | T-174 | Feature flags для ML pipeline (каждая фича/модель включается через YAM | P1 | 2 | done |
| 9.0 | T-148 | Calendar features РФ — праздники + is_weekend + предпраздничные дни | P0 | 1 | done |
| 9.0 | T-145 | submission pipeline — ml/scripts/make_submission.py → submission.csv ( | P0 | 3 | done |
| 8.1 | T-223 | Frontend PassengerMode.tsx — 3 секции (факт / прогноз / таблица) | P0 | 1 | ready |
| 7.0 | T-172 | Events features — инфраструктурные открытия сентября-октября 2025 (Тро | P1 | 2 | done |
| 7.0 | T-163 | docker-compose deploy.resources для всех сервисов + loadtest profile с | P0 | 1.5 | ready |
| 6.0 | T-221 | Frontend routeCsv.ts — парсер CSV + fetch helpers | P0 | 1 | ready |
| 6.0 | T-161 | SLA regression gate — парсинг k6 JSON + блокировка make check-all при  | P0 | 2 | ready |
| 5.4 | T-143 | RealSource для датасета хакатона (route × date × hour boardings) | P0 | 4 | done |
| 5.4 | T-125 | feature engineering — добавить weather и traffic фичи в обучающую выбо | P1 | 2 | ready |
| 5.0 | T-165 | ML training pipeline resource budget + R6 time gate (≤ 60 мин суммарно | P1 | 1.5 | ready |
| 4.8 | T-222 | Frontend PredictionsTable.tsx (TanStack Table) + LastDayCard.tsx | P0 | 1 | ready |
| 4.2 | T-220 | Backend /api/v1/historical/export.csv endpoint (CSV download из actual | P0 | 1 | ready |
| 4.0 | T-224 | Integration: docker rebuild + smoke + ledger + HANDOFF | P0 | 1 | ready |
| 4.0 | T-168 | POI features для маршрутов — schools/universities/stadiums/parks/malls | P1 | 4 | in-progress |
| 3.5 | T-175 | Traffic features (T-124) + GRU нейронка (T-029) + ablation analysis | P1 | 6 | done |
| 3.5 | T-152 | XGBoost retrain с per-route + lag/rolling фичами для WAPE uplift | P0 | 3 | in-progress |
| 3.5 | T-126 | retrain XGBoost на реальных данных с exogenous фичами + измерение импа | P1 | 2 | ready |
| 3.27 | T-173 | CatBoostRoutePredictor + rank-average blend с xgboost_v9_events (T-172 | P1 | 3 | done |
| 3.17 | T-195 | REST API endpoints — historical + predictions (DB) + features + zeros  | P0 | 3 | done |
| 3.15 | T-169 | Anomaly-proneness per route — из остатков train.csv (std residuals по  | P2 | 2 | ready |
| 2.7 | T-218 | PassengerMode переключить на predictions (не actuals) | P0 | 4 | done |
| 2.67 | T-124 | интеграция данных о пробках (Яндекс.Пробки API или OSM fallback) | P1 | 3 | ready |
| 2.67 | T-123 | интеграция погодных данных Open-Meteo (исторические + прогноз) как exo | P1 | 3 | ready |
| 2.5 | T-171 | Deadline prep за 48 часов — final submission + 10-слайдовая презентаци | P0 | 12 | in-progress |
| 2.4 | T-194 | PostgreSQL schema + alembic migrations (T-194) | P0 | 3 | done |
| 1.8 | T-193 | Celery pipeline (harvester + ml-trainer) через Docker | P0 | 4 | done |
| 1.75 | T-038 | ml transit_ai benchmark package configs runner cli report | P1 | 6 | ready |
| 1.75 | T-029 | ml transit_ai models gru pytorch attention pooling | P1 | 6 | ready |
| 1.75 | T-017 | apps/backend Pydantic schemas for prediction request response | P1 | 4 | ready |
| 1.6 | T-139 | apps/mcp — stdio JSON-RPC сервер с 5-7 tools (черновик MCP для Claude  | P2 | 4 | ready |
| 1.5 | T-138 | apps/assistant — LiteLLM провайдер + tools registry + Reasoning (lawco | P2 | 6 | ready |
| 1.5 | T-026 | ml transit_ai data real adapter for hackathon parquet csv json | P1 | 5 | ready |
| 1.4 | T-134 | apps/backend — GET /api/v1/predictions/route/{id}?horizon=month (средн | P1 | 4 | ready |
| 1.4 | T-018 | apps/backend Redis client + cache helper | P1 | 3 | ready |
| 1.2 | T-136 | apps/backend — GET /api/v1/predictions/route/{id}?horizon=year (долгос | P1 | 4 | backlog |
| 1.05 | T-022 | apps/backend Dockerfile + gunicorn config | P2 | 4 | ready |
| 1.05 | T-016 | apps/backend SQLAlchemy 2.0 async session + get_db dependency | P1 | 4 | ready |
| 0.9 | T-225 | Переименовать «Пассажир» → «Диспетчер» в nav, убрать /dispatcher | P2 | 1 | done |
| 0.84 | T-030 | ml transit_ai models hybrid gru lgbm blend | P2 | 5 | ready |
| 0.7 | T-015 | apps/backend alembic init + env migration | P1 | 6 | ready |
| 0.6 | T-140 | ml transit_ai models — GCN+LSTM для пространственно-временного прогноз | P2 | 8 | backlog |

Всего тикетов: 47. Архив выполненных: `docs/backlog/archive/`.
