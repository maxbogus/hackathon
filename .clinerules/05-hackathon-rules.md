# 05-hackathon-rules.md — Hard rules хакатона

## R1. Open-source код

Весь код — Apache 2.0 / MIT / BSD. Не копируем из не-открытых источников.

## R2. Только табличные и небольшие нейронные модели

Можно использовать:
- XGBoost, LightGBM, CatBoost
- PyTorch модели < 4B параметров (GRU, LSTM, небольшие Transformer)
- Линейные модели, ARIMA, Prophet

Нельзя:
- LLM > 4B параметров для inference на хакатоне (запрет организаторов)
- Использовать ChatGPT / Claude / GigaChat для генерации прогнозов (это LLM-as-judge для ассистента — можно)

## R3. Reproducible

Все random seed зафиксированы (numpy, torch, random).
Версии библиотек в `uv.lock` и `yarn.lock` (коммитим).
Docker образ (когда будет) ≤ 15 GB.

## R4. No internet at runtime

Код обучения и inference не должен делать HTTP-запросов к внешним сервисам.
Исключение: наш собственный backend (localhost:8000) и assistant (localhost:8002).

## R5. Real data only

Нельзя тренироваться на синтетике и сдавать как реальный результат.
Синтетика — **только** для разработки скелета и тестов пайплайна.
На хакатоне: заменить `SyntheticSource` на `RealSource`, переобучить, зафиксировать метрики.

## R6. Time limits

Обучение всех моделей суммарно ≤ 60 минут (на RTX 5060 / 4070).
Inference ≤ 2 секунды на запрос диспетчера (SLA из ТЗ).

## R7. API contract

Все эндпоинты документированы в OpenAPI.
Никаких сырых JSON-ответов без схемы.

## R8. Validation report

Перед сабмитом на хакатоне:
1. Запустить `make inventory` → `data/validation_reports/inventory.json`
2. Запустить `make evaluate` → `reports/<model>_metrics.json`
3. Заполнить `docs/HACKATHON_CHECKLIST.md`

## R9. Code review

Каждый PR проверяется как минимум одним участником команды.
Для solo-работы — self-review через `make check-all` + Conventional Commits.

## R10. Презентация и видео

10 слайдов, 5 минут. Структура — `docs/HACKATHON_CHECKLIST.md`.
Видео демо — 2-3 минуты (запись экрана).

## Запрещено

- ❌ Использовать LLM для генерации самого прогноза (только как ассистента)
- ❌ Сдавать синтетические результаты как реальные
- ❌ Подключаться к платным API без ключа команды
- ❌ Использовать данные вне датасета организаторов

## Анти-fraud

Все артефакты (модели, метрики) должны иметь `meta.json` с:
- `git_commit` (хеш коммита, на котором обучена модель)
- `train_data_hash` (sha256 датасета)
- `seed` (random seed)
- `timestamps` (start, end обучения)
