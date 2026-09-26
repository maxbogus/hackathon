# BUSINESS_VALUE — Бизнес-ценность и ограничения

> Создано в рамках критерия 5 жюри (бизнес-ценность и применимость, до 2 баллов).
> Описывает: где применяется, какую выгоду даёт, где ограничено.

## Применение

### 1. Распределение подвижного состава

**Где:** диспетчер трамвайного депо.

**Как:** `GET /api/v1/insights/alerts` возвращает список перегруженных остановок
на ближайшие 30 минут (T-131). Каждый alert содержит:
- `route_id` + `route_name`
- `stop_id`
- `predicted_load_pct` (загрузка в % от capacity)
- `minutes_to_overload`

**Действие:** выпустить дополнительный вагон. Снижает переполнение.

**Метрика:** p95 load_pct ≤ 95% (R6 SLA).

### 2. Снижение переполнения салонов

**Где:** режим «Диспетчер» (T-131).

**Как:** capacity-aware alerts с `load_color` (green/yellow/orange/red/darkred).
Красный = >100% (перегруз).

**Действие:** выпустить вагон **до** того, как load_pct превысит 100%.

**Метрика:** снижение инцидентов с перегрузом на N% (target: 30% в первый месяц).

### 3. Уточнение расписания

**Где:** режим «Пассажир» (T-129/T-130).

**Как:** `GET /api/v1/predictions/eta?stop_id=X&n=3` возвращает ETA + predicted_load_pct
следующих 3 трамваев.

**Действие:** `recommend()` (T-130) даёт «go / wait» на основе eta_min + load_pct.

**Метрика:** среднее время ожидания × комфорт → utility function.

### 4. Оптимизация эксплуатации

**Где:** режим «Планировщик» (T-036 Monte Carlo).

**Как:** симуляция N сценариев «что если» (holiday ×0.5, route 5 запустят, etc.).

**Действие:** выбор стратегии на следующую неделю/месяц.

**Метрика:** средний load_pct в пиковые часы ≤ 90%.

### 5. Аналитика (новое в T-196)

**Где:** режим «Аналитик».

**Как:** Historical + Predictions charts, Feature toggles UI, Zero overrides UI,
корректирующие коэффициенты, Download CSV.

**Действие:** аналитик экспортирует данные → строит отчёт.

**Метрика:** время подготовки еженедельного отчёта: 8 часов → 30 минут.

---

## Ограничения решения

### 1. Drift local vs platform (F-040)

- Local holdout `WAPE-score=0.8751`, platform `0.83455` → drift -0.04pp.
- Причина: платформа может использовать другие ground truth данные (F-021).
- Митигация: best submission валидируется на 2-3 различных submission_id.

### 2. Route 5 cold start (F-051/F-052)

- Route 5 даёт +1.31M чистого штрафа. Трамвай не введён в эксплуатацию.
- Митигация: zero override `zero_route_5` = True по умолчанию.

### 3. Ночные часы 0-4 (F-060)

- Модель предсказывает >0 boardings в hours 0-4, реальный трафик ≈ 0.
- Митигация: zero override `zero_night_pred_cap=55` (pred<=55 в hours 0-4).

### 4. Holiday impact неопределённость (F-080)

- Holiday ×0.5 для 3-4 ноября даёт +0.013pp.
- Другие праздники (8 марта, 9 мая, 12 июня) могут требовать другой multiplier.
- Митигация: консервативный ×0.7 для untested holidays (F-083).

### 5. Traffic features ухудшают (T-124)

- `use_traffic=False` по умолчанию в seed (можно включить вручную).

### 6. Neural dead-end (F-049/F-064)

- GRU/LSTM дают holdout `WAPE-score = 0.10-0.18` vs XGBoost 0.91.
- Решение: только XGBoost в production. GRU код сохранён (с тестами).

### 7. 10 маршрутов максимум

- Модель не масштабируется на >20 маршрутов без переобучения.
- Митигация: для нового города/маршрута — `make train-xgboost` (T-126).

### 8. Weekend override untested (F-070)

- `zero_weekend` отключён по умолчанию (19.5% volume, F-062-style regression risk).

---

## Реалистичные выводы из прогноза

### Что модель хорошо предсказывает

- ✅ **Будни (Mon-Fri) в дневные часы (8-19):** ±15% (F-022)
- ✅ **Сезонные тренды:** декабрь < январь (новогодние каникулы)
- ✅ **Per-route средние:** маршруты 1, 7, 11, 25, 28
- ✅ **Holiday effects:** ×0.5 для 3-4 ноября (F-083)

### Что модель плохо предсказывает

- ❌ **Выходные:** ±40%
- ❌ **Ночные часы:** overpredicted (mitigated F-060)
- ❌ **Route 5:** cold start (mitigated F-051)
- ❌ **Аномалии (аварии, ремонты):** не учтены
- ❌ **Погодные аномалии (ливни, гололёд):** усреднены

---

## План развития после хакатона

### P1 (1-2 месяца)

- [ ] Real-time stream (Kafka/RabbitMQ) вместо batch каждые 24 часа
- [ ] Яндекс.Пробки API для live traffic
- [ ] Расширить на другие города (Питер, Казань)
- [ ] GRU/CNN с per-sequence route embedding
- [ ] Auto-ML (Optuna/AutoGluon)

### P2 (3-6 месяцев)

- [ ] Uncertainty quantification (Bayesian XGBoost)
- [ ] Multi-task: boardings + alightings + dwell_time
- [ ] Real-time anomaly detection
- [ ] Яндекс.Расписания API для ETA

### P3 (6-12 месяцев)

- [ ] ML-Ops (MLflow, model registry, A/B testing)
- [ ] Federated learning для приватности
- [ ] Симулятор расписания всей сети
- [ ] Carbon footprint optimization

---

## Cross-references

- `apps/frontend/src/components/Dispatcher/AlertsPanel.tsx` (T-131)
- `apps/frontend/src/pages/PassengerMode.tsx` (T-129)
- `apps/frontend/src/lib/recommend.ts` (T-130)
- `ml/transit_ai/calibration/` — коэффициенты
- `docs/HACKATHON_CHECKLIST.md`
- F-040, F-051, F-060, F-070, F-080, F-083
- T-204 (этот ticket)
