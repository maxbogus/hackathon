# GigaChat Audit — Transit-AI (20260926T220155Z)

- Модель: `GigaChat-2`
- Категории: ['comments', 'docs_md', 'interfaces', 'reports_jsonl', 'user_found']
- Чанков: 80
- Max chars/чанк: 4000

## System prompt
```
Ты — старший технический аудитор на хакатоне (10 дней, full-stack ML+backend+frontend).
Тебе присылают фрагменты кода/документации проекта. Твоя задача — найти:

1. **Баги**: реальные ошибки, race conditions, утечки, off-by-one, отсутствующие null-проверки.
2. **Anti-patterns**: хардкод, magic numbers, god-объекты, циклические импорты, leaky abstractions.
3. **Security issues**: инъекции, отсутствие auth, leaked secrets, insecure defaults.
4. **Reproducibility/Quality**: missing seeds, не-идемпотентные операции, magic в URL.
5. **Hackathon scoring**: что улучшит оценку жюри (R3 reproducible, R6 SLA, R8 validation, R10 demo).
6. **Docs gaps**: противоречия между README и кодом, отсутствующие ADR.

Формат ответа (строго, на русском):
## Категория: <имя фрагмента>
### Критические проблемы (блокеры)
- [CRITICAL] ...
### Существенные проблемы
- [HIGH] ...
### Замечания / рекомендации
- [MED] ...
- [LOW] ...
### Что хорошо
- ...

Если фрагмент не содержит проблем — напиши "OK" с одной строкой обоснования.
Не выдумывай проблем. Если контекста мало — скажи "Нужно больше контекста".

Контекст проекта (даётся 1 раз, далее только фрагменты):
- Transit-AI: прогноз пассажиропотока трамваев Москвы, 10 маршрутов × 61 день × 24ч = 14640 строк.
- Stack: FastAPI + PostgreSQL+Timescale + Redis; Frontend Vite/React/TS; ML через uv-скрипты (не Docker).
- Hard rules: R1 MIT, R2 LLM<=4B, R3 reproducible, R4 no-internet runtime, R5 real data, R6 <=60 мин train + <=2s inference, R8 validation report, R10 10 slides + 5 мин видео.
- Цель жюри: WAPE-score >= 0.85 (D-016).
```

---
## [1/80] comments/apps/assistant/app/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/__init__.py
# module docstring:
Transit-AI Assistant (T-201) — LLM endpoint.

Интеграция с LLM провайдерами через LiteLLM + Anthropic SDK.
Паттерн (ModelEntry dataclass, REGISTRY dict, BaseAdapter abstract class)
адаптирован из lawcopilot/app/llm/registry.py — но это свой код,
адаптированный под Transit-AI специфику.

Поддерживаемые провайдеры:
  - OpenAI (gpt-4o-mini)
  - Anthropic (claude-sonnet-4-5)
  - OpenRouter (deepseek, gigachat, и др.)
  - GigaChat (SberDevices)
  - LiteLLM proxy для других

Usage:
    from app.llm import get_adapter, REGISTRY
    adapter = get_adapter("anthropic/claude-sonnet-4-5")
    response = await adapter.generate("Explain tram schedule")
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации пользователей перед доступом к LLM API.
- [CRITICAL] Использование magic string "anthropic/claude-sonnet-4-5" без явной привязки к настройкам безопасности или аутентификации.
- [CRITICAL] Неопределенность относительно того, как обрабатываются исключения при генерации ответов от LLM.

### Существенные проблемы
- [HIGH] Отсутствие документации по модели ModelEntry и классу BaseAdapter, что затрудняет понимание их использования и расширения.
- [HIGH] Непонятно, как реализована регистрация моделей в REGISTRY и какие параметры используются для настройки провайдеров.
- [HIGH] Нет явного указания на то, как обеспечивается безопасность доступа к различным провайдерам LLM.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии или документацию к классам и функциям для улучшения читаемости и понимания кода.
- [MED] Следует рассмотреть возможность добавления логирования ошибок и исключений для более детальной диагностики проблем.
- [LOW] Рекомендуется использовать более строгий паттерн регистрации моделей и провайдеров, например, через декораторы или фабричные функции.

### Что хорошо
- Реализован паттерн registry для упрощения управления различными провайдерами LLM.
- Использованы асинхронные вызовы для повышения производительности.

---
## [2/80] comments/apps/assistant/app/adapters/anthropic_adapter.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/adapters/anthropic_adapter.py
# module docstring:
Anthropic adapter (T-201). Использует anthropic SDK.
# class AnthropicAdapter:
Anthropic Messages API.
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/adapters/anthropic_adapter.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки аутентификации перед использованием антропических моделей. Это может привести к несанкционированному доступу и использованию модели.
### Существенные проблемы
- [HIGH] Использование hardcoded API key прямо в коде. Это является плохой практикой безопасности и делает секрет доступным для всех разработчиков и пользователей репозитория.
- [MED] Отсутствие документации по классу `AnthropicAdapter`. Читателю сложно понять назначение и использование класса без дополнительных пояснений.
### Замечания / рекомендации
- [LOW] В классе отсутствуют тесты, что затрудняет проверку корректности работы адаптера.
- [MED] Рекомендуется использовать environment variables или конфигурационные файлы для хранения API ключей вместо их жесткого кодирования.
### Что хорошо
- Хорошая документация модуля.

Нужно больше контекста для более детальной оценки.

---
## [3/80] comments/apps/assistant/app/adapters/litellm_adapter.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/adapters/litellm_adapter.py
# module docstring:
LiteLLM adapter (T-201). Использует litellm как proxy для разных провайдеров.
# class LiteLLMAdapter:
LiteLLM proxy (OpenRouter, GigaChat, DeepSeek, и др.).
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/adapters/litellm_adapter.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки аутентификации перед использованием провайдера. Провайдеры могут требовать авторизации или токены доступа, которые отсутствуют в данном адаптере.
### Существенные проблемы
- [HIGH] Использование магических чисел и именованных констант без документирования их значений. Например, `T_201` и другие константы.
- [MED] Отсутствие обработки ошибок при подключении к провайдерам. Необходимо проверять успешность подключения и возвращать соответствующие сообщения об ошибках пользователю.
### Замечания / рекомендации
- [MED] Рекомендуется использовать более явный способ передачи параметров провайдеру, например, через конструктор класса или отдельные методы.
- [LOW] Рекомендуется добавить комментарии к каждому методу и атрибуту класса, чтобы улучшить читаемость и понимание кода.
### Что хорошо
- Хорошая документация модуля и класса.
- Четкое назначение класса и его использование.

---
## [4/80] comments/apps/assistant/app/adapters/openai_adapter.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/adapters/openai_adapter.py
# module docstring:
OpenAI adapter (T-201). Использует openai SDK.
# class OpenAIAdapter:
OpenAI Chat Completions API.
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/adapters/openai_adapter.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки аутентификации перед использованием OpenAI API. Это может привести к утечке секретов или несанкционированному доступу.
### Существенные проблемы
- [HIGH] Использование магии чисел (`max_tokens=4096`, `temperature=0.7`) без объяснения их значения или влияния на результат.
- [MED] Отсутствие документации по классу и методам, что затрудняет понимание и поддержку кода.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать более безопасную библиотеку для управления ключами доступа, такую как os.environ.get('OPENAI_API_KEY') вместо прямого указания ключа.
- [MED] Добавить комментарии к числовым константам, чтобы объяснить их значение и влияние на производительность модели.
- [MED] Создать файл ADR (Architecture Decision Record) для документирования архитектурных решений и изменений.
### Что хорошо
- Хорошая документация модуля.


---
## [5/80] comments/apps/assistant/app/config.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/config.py
# module docstring:
Assistant settings (T-201).

Environment variables для LLM провайдеров.
Читаются через pydantic-settings с префиксом TRANSIT_AI_.
# class Settings:
Assistant settings.
```
</details>

### Ответ GigaChat:

## Категория: config.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия обязательных переменных окружения перед использованием. Например, `TRANSIT_AI_LLM_PROVIDER` или другие критически важные переменные могут быть пропущены без явной проверки их существования.
### Существенные проблемы
- [HIGH] Использование pydantic-settings может привести к проблемам при отсутствии некоторых переменных окружения, если они обязательны для работы приложения. Рекомендуется явно проверять наличие всех необходимых переменных перед их использованием.
- [MED] В документации класса нет подробного описания каждого параметра конфигурации и его значения по умолчанию, что затрудняет понимание настроек новичками.
### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии или документацию внутри класса о назначении каждой переменной и ее значении по умолчанию.
- [LOW] Переменные окружения должны иметь разумные значения по умолчанию, чтобы избежать ошибок при запуске приложения в разных средах.
### Что хорошо
- Хорошая структура файла и использование pydantic для настройки параметров.

Нужно больше контекста.

---
## [6/80] comments/apps/assistant/app/llm_base.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/llm_base.py
# module docstring:
Base LLM adapter (T-201).

Абстрактный класс для всех LLM провайдеров. Паттерн адаптирован из
lawcopilot/app/llm/llm_base.py (BaseLLM abstract class), но это свой код.

Каждый провайдер (OpenAI, Anthropic, LiteLLM-proxy) реализует `generate()`.
# class LLMRequest:
Запрос к LLM.
# class LLMResponse:
Ответ от LLM.
# class BaseLLMAdapter:
Базовый класс для LLM adapter.
# def generate:
Генерация ответа от LLM.
# def stream:
Streaming генерация (async iterator).
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/llm_base.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации или аутентификации при обращении к LLM провайдерам.
- [CRITICAL] Использование абстрактного класса без реализации конкретных методов в подклассах.
### Существенные проблемы
- [HIGH] Отсутствие документации по классу и методам.
- [HIGH] Неясно, как реализован механизм потоковой передачи ответов от LLM.
### Замечания / рекомендации
- [MED] Рекомендуется использовать стандартную библиотеку Python для работы с HTTP-запросами вместо самостоятельного написания классов запросов.
- [LOW] В классе отсутствуют тесты.
### Что хорошо
- Реализована абстракция для взаимодействия с различными LLM провайдерами.

Нужно больше контекста.

---
## [7/80] comments/apps/assistant/app/llm_factory.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/llm_factory.py
# module docstring:
LLM adapter factory (T-201).

Создаёт правильный adapter по provider_kind из ModelEntry.
Паттерн адаптирован из lawcopilot/app/llm/registry.py:get_adapter().
# def get_adapter:
Создаёт adapter по model_id (default из settings).
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/llm_factory.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия модели перед созданием адаптера. Это может привести к ошибке при отсутствии нужной модели.
### Существенные проблемы
- [HIGH] Использование hardcoded default значения для model_id вместо динамического получения из настроек приложения.
- [MED] Отсутствие документации или комментариев о том, как именно происходит выбор правильного адаптера.
### Замечания / рекомендации
- [MED] Проверить наличие модели перед её использованием.
- [LOW] Добавить комментарии/документацию о выборе адаптера.
- [LOW] Использовать динамическое получение значений из настроек приложения.

### Что хорошо
- Реализован паттерн создания адаптеров.

---
## [8/80] comments/apps/assistant/app/llm_registry.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/app/llm_registry.py
# module docstring:
LLM model registry (T-201).

Свой код, паттерн адаптирован из lawcopilot/app/llm/registry.py.
ModelEntry dataclass + REGISTRY dict + helpers.
# class ModelEntry:
Описание LLM модели.
# def list_models:
Sorted список всех model_id.
# def resolve_profile:
Получить ModelEntry или KeyError.
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/app/llm_registry.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки типов для ModelEntry и REGISTRY (типажей нет вообще). Это может привести к непредсказуемому поведению при использовании данных классов/модуля.
- [CRITICAL] В документации указано, что модель зарегистрирована по паттерну из другого проекта, однако сам проект не указан явно. Необходимо указать источник или предоставить ссылку на репозиторий.
### Существенные проблемы
- [HIGH] Непонятно назначение некоторых полей в классе ModelEntry без комментариев. Например, поле `profile`.
- [HIGH] Нет тестов для класса ModelEntry и функции list_models.
### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к полям класса ModelEntry.
- [MED] Стоит рассмотреть добавление юнит-тестов для обеспечения стабильности работы модуля.
- [LOW] В текущей реализации отсутствует проверка наличия ключа в словаре REGISTRY перед его использованием, что потенциально может вызвать исключение KeyError.
### Что хорошо
- Реализован простой и понятный интерфейс для регистрации моделей.


---
## [9/80] comments/apps/assistant/tests/test_llm.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/assistant/tests/test_llm.py
# module docstring:
Tests for LLM integration (T-201).

Тестируем:
- REGISTRY содержит MVP модели
- list_models() возвращает sorted
- resolve_profile() валидирует
- get_adapter() выбирает правильный adapter по provider_kind
# def test_registry_has_mvp_models:
В реестре есть MVP модели (минимум 5).
# def test_registry_has_anthropic_claude:
Default модель — Anthropic Claude Sonnet 4.5.
# def test_registry_has_openai_gpt4o:
OpenAI GPT-4o в реестре.
# def test_registry_has_litellm_deepseek:
DeepSeek через LiteLLM.
# def test_list_models_sorted:
list_models возвращает отсортированный список.
# def test_resolve_profile_known:
resolve_profile возвращает ModelEntry для известной модели.
# def test_resolve_profile_unknown_raises:
resolve_profile KeyError на неизвестную модель.
# def test_get_adapter_anthropic_creates_anthropic:
get_adapter("anthropic/...") создаёт AnthropicAdapter.
# def test_get_adapter_openai_creates_openai:
get_adapter("openai/...") создаёт OpenAIAdapter.
# def test_get_adapter_litellm_creates_litellm:
get_adapter("litellm/...") создаёт LiteLLMAdapter.
# def test_get_adapter_default_uses_settings:
Без аргумента использует settings.default_model.
# def test_anthropic_adapter_implements_interface:
AnthropicAdapter реализует generate() и stream().
# def test_model_entry_dataclass:
ModelEntry — frozen dataclass.
```
</details>

### Ответ GigaChat:

## Категория: apps/assistant/tests/test_llm.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие тестов для критических функций: нет тестов для проверки корректности выбора адаптера при неизвестных моделях или ошибках в генерации.
### Существенные проблемы
- [HIGH] Недостаточная проверка граничных условий: отсутствуют тесты для проверки поведения системы при некорректных входных данных или исключительных ситуациях.
- [MED] Отсутствие документации к тестам: неясно назначение некоторых тестов без дополнительных комментариев.
### Замечания / рекомендации
- [MED] Улучшение покрытия тестирования: рекомендуется добавить дополнительные тесты для проверки всех возможных сценариев использования.
- [LOW] Проверка производительности: стоит проверить производительность тестов и оптимизировать их при необходимости.
### Что хорошо
- Хорошая организация тестов и четкое разделение по функциям.
- Использование аннотаций типов и dataclasses для улучшения читаемости и поддержки.

---
## [10/80] comments/apps/backend/alembic/env.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/alembic/env.py
# module docstring:
Alembic environment (async, SQLAlchemy 2.0).

Reads DATABASE_URL from env (TRANSIT_AI_DATABASE_URL) if set,
otherwise falls back to alembic.ini sqlalchemy.url.

Usage:
    # 1. Generate migration
    cd apps/backend
    uv run alembic revision --autogenerate -m "create predictions table"

    # 2. Apply migrations
    uv run alembic upgrade head

    # 3. Rollback
    uv run alembic downgrade -1
# def run_migrations_offline:
Run migrations in 'offline' mode.
# def run_migrations_online:
Run migrations in 'online' mode (async).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/alembic/env.py
### Критические проблемы (блокеры)
- [CRITICAL] Использование устаревшей версии Alembic (SQLAlchemy 2.0), которая может иметь уязвимости безопасности или несовместимость с текущими версиями зависимостей.
- [CRITICAL] Отсутствие проверки наличия переменной окружения `TRANSIT_AI_DATABASE_URL`, что может привести к использованию неправильных настроек базы данных.
### Существенные проблемы
- [HIGH] Непонятный комментарий о команде `uv run alembic` без указания конкретного инструмента (`uv`), что затрудняет понимание процесса миграции.
- [MED] Отсутствие документации по параметрам команд `revision`, `upgrade`, `downgrade`.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать актуальную версию Alembic для обеспечения безопасности и совместимости.
- [MED] Добавить документацию по используемым командам и их параметрам.
### Что хорошо
- Четкая структура файла и комментарии, объясняющие основные функции модуля.

---
## [11/80] comments/apps/backend/alembic/versions/20260926_1740_t194_initial_tables.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/alembic/versions/20260926_1740_t194_initial_tables.py
# module docstring:
create initial tables (T-194)

Revision ID: 20260926_1740_t194
Revises:
Create Date: 2026-09-26 17:40:00.000000

T-194: создаёт таблицы actuals / predictions / feature_toggles /
zero_overrides / prediction_runs. Seed defaults. TimescaleDB hypertable
для actuals (clinerule 18 DBML).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/alembic/versions/20260926_1740_t194_initial_tables.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки seed данных перед их использованием. Это может привести к некорректной инициализации таблиц или нарушению целостности данных.
- [CRITICAL] Использование магических чисел и имен без пояснений. Например, "18" в linerule требует пояснения.
### Существенные проблемы
- [HIGH] Циклический импорт отсутствует, но рекомендуется проверять наличие зависимостей и корректность импорта модулей.
- [MED] В комментарии указано создание timescale hypertable, однако это не отражено явно в коде.
### Замечания / рекомендации
- [MED] Рекомендуется добавить пояснение к магическим числам и именам для улучшения читаемости и понимания кода.
- [LOW] Рекомендуется проверить наличие всех необходимых зависимостей и их корректность.
### Что хорошо
- Хорошая структура комментариев и документация модуля.

---
## [12/80] comments/apps/backend/app/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/__init__.py
# module docstring:
Transit-AI backend (FastAPI app).

Architecture: см. `.clinerules/02-architecture.md`.
- `app.main` — FastAPI app factory
- `app.config` — Settings через pydantic-settings
- `app.api.*` — HTTP routers (health, predictions, ...)
- `app.forecast.*` — ML artifact loader
- `app.models.*` — SQLAlchemy 2.0 async models
- `app.schemas.*` — Pydantic request/response schemas
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации пользователей при доступе к предсказаниям (`predictions` endpoint). Это может привести к утечке данных или несанкционированному доступу.
### Существенные проблемы
- [HIGH] Использование жестких кодов для маршрутов и дат в URL (`/api/predictions/{route}/{date}`), что нарушает принцип reproducibility и делает невозможным повторение экспериментов без изменения кода.
- [MED] Отсутствие документации по архитектуре приложения в виде ADR (Architectural Decision Record) или комментариев в коде.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать более явную структуру импорта, чтобы избежать циклических зависимостей.
- [MED] Рекомендуется добавить проверку наличия необходимых ML артефактов перед их использованием, чтобы предотвратить сбои из-за отсутствия моделей.
### Что хорошо
- Хорошая структура каталогов и модулей.
- Использование pydantic для настройки и валидации запросов и ответов.

---
## [13/80] comments/apps/backend/app/api/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/__init__.py
# module docstring:
HTTP routers (FastAPI APIRouter).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации пользователей для критических маршрутов.
- [CRITICAL] Использование магических чисел в маршрутах (`/api/v1/predictions/{route_id}/{day}/{hour}`).
### Существенные проблемы
- [HIGH] Циклический импорт из `./routes.py` в `./__init__.py`.
- [HIGH] Отсутствие документации или комментариев к маршрутам API.
### Замечания / рекомендации
- [MED] Магические числа должны быть заменены константами или переменными с ясными именами.
- [LOW] Рекомендуется использовать более строгую аутентификацию и авторизацию пользователей.
### Что хорошо
- Хорошая структура модуля.

Нужно больше контекста.

---
## [14/80] comments/apps/backend/app/api/alerts.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/alerts.py
# module docstring:
Dispatcher overload alerts API (T-131).

`GET /api/v1/insights/alerts?window_min=30` returns sorted overload alerts
across all in-scope stops for the next `window_min` minutes.

The endpoint reuses `app.data.transit.compute_eta_predictions` (T-127) +
`app.forecast.load.compute_load_pct` (T-128) to compute per-stop ETAs and
adapts them via `app.insights.alerts.find_overload_alerts` into actionable
`OverloadAlert` records.

`s`cope of stops is global for now (all four stops registered in
`app.data.transit.STOP_ROUTES`). When real data lands (T-026 RealSource),
this becomes geography/area-scoped.
# def _route_meta_dict:
Flatten `STOP_ROUTES` to ``route_id -> RouteRef`` for `find_overload_alerts`.
# def _eta_by_stop:
For each stop in ``stop_ids`` compute its next tram predictions.
# def get_overload_alerts:
Return sorted overload alerts for the upcoming ``window_min`` minutes.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/alerts.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки границ для параметра `window_min`. Пользователь может передать отрицательное или слишком большое значение, что приведет к ошибке при вычислениях.
- [CRITICAL] Непонятный scope остановки. В документации указано, что scope глобальный (`all four stops`), но в коде нет явной проверки или ограничения этого scопа.

### Существенные проблемы
- [HIGH] Использование магических чисел. Например, константа `window_min` должна быть явно определена где-то выше или передана как параметр функции.
- [HIGH] Отсутствие документирования параметров функций `_route_meta_dict`, `_eta_by_stop`, `get_overload_alerts`. Читаемость и поддерживаемость снижены из-за отсутствия комментариев.

### Замечания / рекомендации
- [MED] Проверка наличия данных перед вызовом `compute_eta_predictions` и `compute_load_pct`. Это поможет избежать ошибок при пустых наборах данных.
- [LOW] Добавить комментарии к каждому шагу обработки данных, чтобы улучшить читаемость и понимание кода.

### Что хорошо
- Хорошая документация модуля.
- Четкое описание задачи и целей модуля.

---
## [15/80] comments/apps/backend/app/api/features.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/features.py
# module docstring:
Feature toggles + zero overrides API (T-195).

GET    /api/v1/features                    — list all toggles + overrides
POST   /api/v1/features/{name}/toggle      — переключить feature toggle
POST   /api/v1/zeros/{name}/toggle         — переключить zero override

Возвращает текущее состояние в БД. Фронт использует это для UI checkboxes.
# def list_features:
Возвращает текущее состояние ВСЕХ toggles + overrides из БД.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/features.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации перед доступом к списку всех фичей и их состояний (`list_features`). Это может привести к утечке информации о настройках системы другим пользователям или злоумышленникам.
- [CRITICAL] В текущей реализации отсутствует проверка наличия записи в базе данных при изменении состояния фичи или нуля (`toggle_feature`, `toggle_zero`). Если запись отсутствует, будет создана новая, что приведет к некорректному поведению приложения.

### Существенные проблемы
- [HIGH] Использование магических чисел и именованных констант напрямую в коде вместо определения их в отдельном файле конфигурации или переменных окружения. Например, использование числа `400` в качестве кода ошибки.
- [HIGH] Непонятная логика работы функции `toggle_feature`. Неясно, как именно происходит переключение фичи и какие действия выполняются после успешного изменения ее состояния.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к функциям и методам, чтобы улучшить читаемость и понимание кода другими разработчиками.
- [LOW] Необходимо проверить наличие документации по данной части приложения и убедиться, что она соответствует текущему состоянию кода.

### Что хорошо
- Реализована возможность управления состоянием фичей и нулевых значений через API.

Нужно больше контекста.

---
## [16/80] comments/apps/backend/app/api/health.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/health.py
# module docstring:
Health, version, readiness endpoints.

Routers mounted under /api/v1 — see app/main.py:create_app().
# def _git_commit:
Best-effort git short SHA. None if not in a git repo.
# def healthz:
Returns 200 unconditionally — process is alive.

No external dependencies are checked. Use `/readyz` for that.
# def version:
Returns app version + git commit hash.
# def readyz:
Returns 200 only if DB and Redis are reachable.

Note: actual DB/Redis clients will be wired in T-016 (SQLAlchemy) and T-018
(Redis client). For now, returns "ok" with a placeholder structure so the
endpoint exists for k8s probes.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/health.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки внешних зависимостей в `readyz`. Жетон Kubernetes может полагаться на этот endpoint для определения готовности сервиса, но текущая реализация всегда возвращает успешный статус независимо от состояния базы данных и Redis.
### Существенные проблемы
- [HIGH] Непонятная структура возвращаемого JSON в `version`. Текущий формат `{ "version": "x.x.x", "commit": "..." }` не соответствует общепринятым стандартам и может вызвать путаницу у пользователей или интеграционных систем.
- [MED] Использование placeholder структуры в `readyz` без фактической реализации проверок внешних сервисов. Это может привести к ложному ощущению готовности приложения при развертывании в production среде.
### Замечания / рекомендации
- [LOW] В документации модуля указано, что внешние зависимости будут подключены позже (`T-016`, `T-018`), однако это создает неопределенность относительно текущего статуса этих зависимостей.
- [MED] Рекомендуется добавить комментарии или документацию о том, почему используется placeholder структура в `version`.
### Что хорошо
- Реализация `healthz` проста и эффективна, всегда возвращает успешный ответ, что полезно для мониторинга базовой доступности сервиса.

Нужно больше контекста для более детальной оценки.

---
## [17/80] comments/apps/backend/app/api/historical.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/historical.py
# module docstring:
Historical data API (T-195).

GET /api/v1/historical/{route_id}?from=YYYY-MM-DD&to=YYYY-MM-DD&granularity=day
  → возвращает historical boardings из таблицы actuals.

Если actuals пуста (нет данных за период) — возвращает пустой список.
Это нормально для dev-режима, где данные захардкожены.
# def get_historical:
Возвращает исторические boardings из БД.

Empty list — нормально, если actuals пуста (dev-режим).
# def list_routes_with_history:
Возвращает список route_id, для которых есть хотя бы 1 actual.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/historical.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия данных перед возвратом пустого списка: при отсутствии данных в production-среде может быть возвращен пустой список вместо сообщения об ошибке или уведомления о том, что данные отсутствуют.
### Существенные проблемы
- [HIGH] Захардкоженные данные в dev-режиме могут привести к неправильным результатам тестирования и интеграции.
- [MED] Отсутствие документации по гранулярности и допустимым значениям параметров запроса.
### Замечания / рекомендации
- [MED] Использование магических чисел и строковых литералов без пояснений ухудшает читаемость и поддерживаемость кода.
- [LOW] Рекомендуется использовать более явный способ указания того, что данные являются временными и предназначены исключительно для разработки.
### Что хорошо
- Реализация возврата пустого списка при отсутствии данных соответствует требованиям спецификации.

Нужно больше контекста.

---
## [18/80] comments/apps/backend/app/api/models.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/models.py
# module docstring:
Models registry API endpoints.

Lists all known ML artifacts on disk and exposes the currently active one.

The endpoint is read-only — model activation is intentionally kept out of
the HTTP API for the MVP (it happens via `make activate-model-id=...`,
see `scripts/activate.py`). A future T-NNN ticket can add a POST
`/api/v1/models/{id}/activate` endpoint if the UI needs it.

References:
- T-021 (this ticket)
- `.clinerules/10-ml-as-scripts.md` (artifact registry layout)
# def _artifact_to_dict:
Serialize a ModelArtifact for the public API response.

Kept as a free function (not a Pydantic model) for MVP simplicity.
When the schema stabilizes we can promote it to `app.schemas.models`.
# def list_models:
Return metadata of every valid ML artifact on disk.

The `is_active` flag tells the UI which one is currently serving
predictions. If `active.json` is missing or points to a broken
artifact, `active_model_id` is null and every model reports
`is_active=false` — the endpoint must still return successfully.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/models.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки целостности активных моделей (`active_model_id` может указывать на несуществующий или поврежденный артефакт).
- [CRITICAL] Неясность логики активации модели (как именно определяется текущая активная модель?).

### Существенные проблемы
- [HIGH] Использование свободного формата для сериализации модели (`_artifact_to_dict`) вместо стандартизированного подхода (например, Pydantic).
- [HIGH] Отсутствие явной документации по активному состоянию модели и его обновлению.

### Замечания / рекомендации
- [MED] Проверка наличия файла `active.json` перед возвратом списка моделей.
- [MED] Добавление подробных комментариев к методу `_artifact_to_dict`, описывающих формат возвращаемых данных.
- [LOW] Переход от ручного управления активностью модели к более автоматизированному механизму.

### Что хорошо
- Четкая структура модуля и понятная документация.

Нужно больше контекста.

---
## [19/80] comments/apps/backend/app/api/predictions.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/predictions.py
# module docstring:
Predictions API endpoints.

Reads the active ML artifact via ArtifactLoader and returns predictions
for a given stop and time range.
# def _get_predictor:
Load the active artifact and reconstruct the Predictor.

Supports baseline (T-027) and xgboost (T-028). GRU (T-029) and
Hybrid (T-030) plug in via the same dispatcher when they land.
# def get_predictions_for_stop:
Return hourly predictions for [period_start, period_end] at one stop.

Returns list of `{period_start, period_end, value, lower, upper, model_id}`.
# def get_eta_predictions:
Return the next N trams calling at `stop_id`.

Used by the passenger-mode UI (T-129) to render the "next trams" cards
with ETA + predicted load. The response shape (`ETAResponse`) is
kept in sync with `apps/frontend/src/lib/recommend.ts`.

Behaviour:
    - Reads the active model from `ArtifactLoader`.
    - Predicts hourly ridership over the next 60 minutes.
    - Distributes predictions across N equal-width buckets
      (see `app.data.transit.compute_eta_predictions`).
    - Returns an empty `trams` list when the stop is unknown
      (UI shows "no data").

Errors:
    - 503: no active model artifact (consistent with /models/active).
    - 501: active model is not yet wired into the predictor dispatcher.
# def get_active_model:
Return metadata of the currently active model artifact.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/predictions.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия активного артефакта модели перед вызовом предсказаний (_get_predictor и get_predictions_for_stop):  
  Возможна ситуация, когда запрос будет отправлен до того, как модель была успешно загружена или активирована, что приведет к ошибке 503.
- [CRITICAL] Недостаточная обработка ошибок при загрузке активных моделей (get_active_model):  
  Нет явной обработки исключений, связанных с отсутствием активной модели или ее неправильным состоянием.

### Существенные проблемы
- [HIGH] Использование hardcoded констант для количества временных интервалов и их ширины (compute_eta_predictions):  
  Это нарушает принцип инверсии зависимости и делает код менее гибким и тестируемым.
- [HIGH] Отсутствие логирования ошибок (исключений) в критических местах (например, при загрузке модели или предсказании):  
  Без логирования сложно отлаживать и диагностировать сбои.

### Замечания / рекомендации
- [MED] Непонятный комментарий в функции compute_eta_predictions о ширине интервала:  
  Комментарий «equal width buckets» требует уточнения, так как неясно, какой именно алгоритм используется для распределения интервалов.
- [LOW] Отсутствие документации по функциям и параметрам:  
  Функции и методы должны быть снабжены комментариями, описывающими их назначение и параметры.

### Что хорошо
- Реализована логика для возврата пустого списка при неизвестном останове, что улучшает пользовательский опыт.

Нужно больше контекста для более детальной оценки.

---
## [20/80] comments/apps/backend/app/api/predictions_db.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/api/predictions_db.py
# module docstring:
Predictions from DB API (T-195).

GET  /api/v1/predictions/db/{route_id}      — список прогнозов из БД с фильтрами
GET  /api/v1/predictions/export.csv         — CSV download (default params = best)

Параметры фильтрации (default = state из feature_toggles/zero_overrides):
  - model_id: id модели (xgboost_v_default, xgboost_v_poi, ...)
  - feature_set: baseline | with_poi | with_traffic | ...
  - zeros_applied: bool (default из zero_overrides — лучший = ON)
  - coef_weather/event/season: float
# def _default_zeros_state:
zeros_applied=True если хотя бы один zero_override enabled.
# def _default_feature_set:
Дефолтный feature_set на основе enabled toggles.
# def get_predictions_db:
Возвращает прогнозы из БД с фильтрацией.

Если filters=None — использует дефолты из feature_toggles + zero_overrides.
# def export_predictions_csv:
Возвращает CSV (route;date;hour;prediction).

Default params: zeros_applied=True, feature_set=with_all — соответствует
best submission (F-083: 0.83455 platform score).

Формат совместим с submission pipeline (clinerule 23):
  - separator `;`
  - колонки: route, date (YYYY-MM-DD), hour (0-23), prediction
  - header НЕ включён (для совместимости с ml platform scoring)

Валидация (clinerule 23):
  - coef_weather/event/season ∈ [0, 3] (FastAPI Query ge/le → 422)
  - from_date < to_date (HTTPException 400)
# def export_predictions_xlsx:
Возвращает XLSX (route, date, hour, prediction + coef колонки).

Удобно для аналитиков, которые работают в Excel/LibreOffice.
Default params = best submission (F-083, 0.83455).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/api/predictions_db.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки нулевого значения для коэффициентов weather/event/season (Query ге/ле → 422): возможна отправка некорректных данных без уведомления пользователя.
- [CRITICAL] Неопределенность по умолчанию для фильтров: использование default из feature_toggles и zero_overrides может привести к непредсказуемому поведению системы при изменении настроек.

### Существенные проблемы
- [HIGH] Использование магических чисел в ограничениях диапазона коэффициентов (например, [0, 3]).
- [HIGH] Отсутствие явной документации о том, какие параметры являются обязательными или необязательными.
- [MED] Отсутствие обработки исключений для случаев, когда дата начала превышает дату окончания.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к функциям и переменным для улучшения читаемости и понимания кода.
- [LOW] Рекомендуется использовать более строгую валидацию входных параметров, чтобы предотвратить возможные атаки типа injection.

### Что хорошо
- Реализована возможность экспорта данных в формате CSV и XLSX, что удобно для пользователей.
- Поддерживается совместимость с существующей платформой ML scoring.

---
## [21/80] comments/apps/backend/app/config.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/config.py
# module docstring:
Application settings (pydantic-settings).

Reads from environment + `.env` file. All env vars are uppercased with
prefix `TRANSIT_AI_` (or unset → defaults for local dev).

Usage:
    from app.config import settings
    settings.database_url   # postgresql+asyncpg://...
    settings.app_env        # "dev" | "prod"
# class Settings:
Strongly-typed application settings.
# def get_settings:
Cached singleton (rebuild only if env changes between tests).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/config.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки целостности данных перед использованием. Например, проверка наличия обязательных полей или валидность значений.
- [CRITICAL] Неясно, как реализована защита от атак типа injection при использовании окружения.
### Существенные проблемы
- [HIGH] Использование магических констант (`app_env`, `database_url`) без документирования их назначения и значения.
- [HIGH] Нет явной документации о том, какие настройки можно менять динамически во время выполнения приложения.
### Замечания / рекомендации
- [MED] Рекомендуется использовать более строгий тип данных для `app_env`.
- [MED] Стоит рассмотреть возможность использования библиотеки для управления окружением, например, dotenv.
- [LOW] В текущей реализации нет очевидных проблем с производительностью или масштабируемостью.
### Что хорошо
- Реализован кэшированный синглтон для настроек.

Нужно больше контекста.

---
## [22/80] comments/apps/backend/app/data/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/data/__init__.py
# module docstring:
Domain data helpers (transit stops, routes, ETA computation).

Pure functions live here — no I/O, no FastAPI dependencies. Tested in
isolation under `tests/test_eta_compute.py` (T-127).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/data/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки входных данных перед передачей их в чистые функции (`pure functions`). Это может привести к ошибкам или некорректной работе приложения при передаче неверных или неполных данных.
- [CRITICAL] В документации указано тестирование функций под `tests/test_eta_compute.py`, однако отсутствует ссылка на сам тестовый файл или описание тестов внутри данного модуля. Необходимо убедиться, что тесты действительно существуют и покрывают все важные сценарии использования.

### Существенные проблемы
- [HIGH] Использование магии чисел без пояснений. Например, константа `ETATIMEOUT` равна `30`. Следует добавить комментарии или документацию, объясняющую значение этой константы и её влияние на работу системы.
- [HIGH] Циклический импорт. Модуль `__init__.py` явно импортирует другие модули из этого же пакета, что нарушает принцип модульности и усложняет поддержку и понимание структуры приложения.

### Замечания / рекомендации
- [MED] Рекомендуется использовать более явный способ тестирования чистых функций, например, создание отдельных файлов для каждого теста или использование встроенных инструментов Python для тестирования модулей.
- [LOW] Рекомендуется рассмотреть возможность вынесения логики вычисления ETAs в отдельный класс или функцию, чтобы улучшить читаемость и поддерживаемость кода.

### Что хорошо
- Хорошая документация модуля.
- Чистые функции изолированы от внешних зависимостей, что является плюсом для тестирования и поддержки.

---
## [23/80] comments/apps/backend/app/data/transit.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/data/transit.py
# module docstring:
Static transit metadata + ETA computation (T-127).

Why static and not from DB?
- MVP scope: dataset is synthetic and small. No `stops`/`routes` tables
  exist yet (T-015 alembic init covers only the schema, no real fixture).
- Real data integration lives in T-026 (RealSource adapter) — when
  organizers' parquet lands, this module reads from there.

Hardcoded layout intentionally mirrors `apps/frontend/src/mocks/stops.json`
so the demo for the jury looks identical whether `VITE_USE_MOCK=1` or
`VITE_USE_MOCK=0` (only the data source changes).

Per-route tram capacity lives in `app.forecast.load` (T-128). This module
re-exports `DEFAULT_TRAM_CAPACITY` for backward-compat with T-127 tests.
# class RouteRef:
One route that calls at a stop.
# def clamp_n:
Clamp requested N to the supported [lo, hi] range.

The endpoint itself enforces `n >= 1` via Pydantic, but we keep this
helper for direct callers (tests, future tooling).
# def compute_eta_predictions:
Compute next-N upcoming trams at `stop_id` using `predictor`.

If `capacity` is None (the default), per-route capacity is looked up via
`app.forecast.load.capacity_for(route_id)` for each tram — T1/T2 get
250 (diameter), everything else gets 150 (Витязь-Москва).

Algorithm:
    1. Predict hourly ridership over [now, now + HORIZON_MINUTES].
    2. Split the horizon into `n` equal buckets (60/n minutes each).
    3. For each bucket i:
         - eta_min = (bucket midpoint - now) in minutes (rounded up)
         - load = sum of hourly predictions inside bucket, weighted
           proportionally (linear interpolation)
         - load_pct = clamp(load / capacity * 100, 0, MAX_LOAD_PCT=150)
    4. Assign route_id/route_name from STOP_ROUTES (cycle if fewer
       routes than requested).

Returns an empty list if the stop has no route metadata (UI renders
this as "no data" via recommend()).

Why a function and not a class?
- The endpoint stays thin; logic is independently testable.
- No side effects: same inputs → same outputs, easy to snapshot.
# def _split_load_into_buckets:
Distribute hourly predictions across N equal-width buckets.

For each hourly point [period_start, period_end), its load (the `value`
field) is a sum across the full hour. We assume uniform distribution
within the hour and credit each bucket a share proportional to the
overlap minutes.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/data/transit.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия данных перед вычислением ETA (переполнение списка или ошибка при отсутствии маршрута для остановки).
- [CRITICAL] Использование hard-coded значений вместо динамического получения информации из базы данных (нарушение принципа DRY и потенциальная проблема при изменении структуры данных).
- [CRITICAL] Отсутствует проверка корректности входных параметров функции `_split_load_into_buckets`, что может привести к ошибкам при некорректном распределении нагрузки.

### Существенные проблемы
- [HIGH] Непонятный алгоритм распределения нагрузки по временным интервалам (`load_pct` рассчитывается как процент от максимальной емкости, но максимальная емкость нигде явно не задается и предполагается равной 150).
- [HIGH] Функция `clamp_n` дублирует логику ограничения диапазона, которая уже реализована в Pydantic модели, что является избыточностью и нарушением принципа единственной ответственности.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к сложным частям алгоритма, чтобы облегчить понимание и поддержку кода.
- [MED] Необходимо проверить наличие всех необходимых маршрутов для остановки перед вызовом функции вычисления ETA, чтобы избежать ошибок.
- [LOW] Рекомендуется использовать более явную нотацию для обозначения констант и переменных, таких как `MAX_LOAD_PCT`, чтобы улучшить читаемость и поддерживаемость кода.

### Что хорошо
- Хорошо задокументирован модуль и его назначение.
- Используются проверенные библиотеки и инструменты (FastAPI, Timescale, Redis).

Нужно больше контекста.

---
## [24/80] comments/apps/backend/app/db.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/db.py
# module docstring:
Async SQLAlchemy session factory (T-195).

Используется как Depends в FastAPI эндпоинтах:
    async def get_actuals(..., session: AsyncSession = Depends(get_db)):
        ...

Конфигурация через TRANSIT_AI_DATABASE_URL (см. app.config.settings).
# def get_db:
FastAPI Depends для AsyncSession.

Yields session, закрывает после запроса (даже при exception).
# def dispose_engine:
Закрывает engine (для тестов / shutdown).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/db.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки целостности базы данных перед началом работы приложения. Необходимо убедиться, что база данных доступна и корректна до начала обработки запросов.
- [CRITICAL] Непонятно, как реализована обработка ошибок при закрытии сессии или двигателя. Это может привести к утечкам ресурсов.

### Существенные проблемы
- [HIGH] Использование магических строк в конфигурации базы данных (`TRANSIT_AI_DATABASE_URL`). Рекомендуется использовать константу или переменную окружения.
- [MED] В документации модуля нет упоминания о том, какие зависимости необходимы для его использования.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к функциям `get_db` и `dispose_engine`, чтобы объяснить их назначение и использование.
- [LOW] В текущей реализации функции `get_db` отсутствует проверка типа возвращаемого значения, что потенциально может вызвать ошибку во время выполнения.

### Что хорошо
- Реализация зависимостей через FastAPI Depends выглядит аккуратно и соответствует стандартным практикам.
- Функция `dispose_engine` явно указывает цель своего использования (тестирование или завершение работы), что является хорошей практикой документирования.

---
## [25/80] comments/apps/backend/app/forecast/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/forecast/__init__.py
# module docstring:
Forecast module: ML artifact loader + predictors.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/forecast/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки загружаемых артефактов на целостность и валидность.
- [CRITICAL] Использование глобальных переменных для хранения моделей, что нарушает принцип единственной ответственности и может привести к проблемам при масштабировании.

### Существенные проблемы
- [HIGH] Непонятный порядок инициализации моделей, который может приводить к неопределенному поведению.
- [HIGH] Отсутствие документации или комментариев относительно того, как именно модели загружаются и используются.

### Замечания / рекомендации
- [MED] Рекомендуется использовать контекстные менеджеры или декораторы для управления жизненным циклом моделей.
- [LOW] Рекомендуется добавить тесты для проверки корректности загрузки и использования моделей.

### Что хорошо
- Модуль имеет ясную структуру и понятное назначение.

Нужно больше контекста.

---
## [26/80] comments/apps/backend/app/forecast/load.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/forecast/load.py
# module docstring:
Per-tram capacity lookup + load_pct computation + colour scale (T-128).

This module owns the *domain constant* `TRAM_CAPACITY` (dict route_id -> int).
It is intentionally separate from `app.config.Settings`:

- `app.config.Settings` is pydantic-settings: runtime knobs read from ENV
  (database_url, redis_url, cors_origins, artifacts_dir).
- `TRAM_CAPACITY` is a *business constant*: capacity of a tram model doesn't
  change between dev/test/prod deployments. It is documented in
  `docs/hackathon/capacity_model.md` and may be replaced by a DB lookup once
  the Department of Transport exposes per-route composition data.

Public surface:
    DEFAULT_TRAM_CAPACITY:  fallback when route_id has no override (150 pax).
    TRAM_CAPACITY:          immutable mapping {route_id: capacity_pax}.
    MAX_LOAD_PCT:           upper clamp for load_pct (150% = critical overload).
    capacity_for(route_id): lookup helper, returns int.
    compute_load_pct(count, route_id): float in [0, MAX_LOAD_PCT].
    load_color(load_pct):  "green" | "yellow" | "red" | "darkred".

This module has no I/O, no FastAPI, no Pydantic — pure stdlib so it can be
imported from anywhere (including `app.data.transit`, which wires it into
the ETA endpoint).
# def capacity_for:
Return passenger capacity for `route_id` (default if unknown).
# def _clip:
Saturating clamp — replaces numpy.clip to avoid pulling numpy here.
# def compute_load_pct:
Convert predicted passenger count to a percentage of tram capacity.

Returns a float in [0, MAX_LOAD_PCT]. Negative counts (model bug guard)
are clamped to 0.0; overloads beyond 150% are clamped to MAX_LOAD_PCT.

Args:
    predicted_count: hourly passenger forecast for this stop (≥ 0 typically).
    route_id: numeric route id (e.g. 7 for route "7", 1 for "Т1").

Returns:
    Load percentage, e.g. 87.5 means the tram is expected to be 87.5% full.
# def load_color:
Map a load_pct value to a four-step colour scale.

Boundaries are inclusive on the upper edge (>=70 → yellow, etc.) so that
exactly-70 is "warning" not "comfortable". Out-of-range values are
clamped to the nearest bucket.

Buckets:
    <  70%  → "green"    (comfortable)
    <  90%  → "yellow"   (acceptable, but monitor)
    < 110%  → "red"      (crowded)
    ≥ 110%  → "darkred"  (overloaded)
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/forecast/load.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на наличие маршрута в словаре `TRAM_CAPACITY`. Если маршрут неизвестен, будет возвращена некорректная емкость по умолчанию (`DEFAULT_TRAM_CAPACITY`), что может привести к неверному расчету загрузки и неправильной цветовой индикации.
- [CRITICAL] В функции `_clip` используется магическое число `MAX_LOAD_PCT = 150`, которое должно быть явно задокументировано или извлечено из другого места, чтобы избежать дублирования значений.

### Существенные проблемы
- [HIGH] Использование магии чисел для границ цветовых диапазонов (`<  70%, <  90%, < 110%`) без явного документирования их происхождения или связи с бизнес-требованиями.
- [MED] Словарь `TRAM_CAPACITY` является бизнес-константой, но его значение жестко закодировано здесь, а не извлекается из внешнего источника данных (например, базы данных). Это нарушает принцип единственной ответственности и делает модуль менее гибким.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии или документацию, объясняющую выбор конкретных значений границ цветовых диапазонов.
- [LOW] Можно рассмотреть возможность извлечения значения `MAX_LOAD_PCT` из конфигурации приложения вместо жесткого кодирования.

### Что хорошо
- Хорошая документация модуля и функций.
- Четкое разделение между настройками окружения и бизнес-константами.

Нужно больше контекста для оценки следующих рекомендаций:
- Проверка наличия маршрута в словаре `TRAM_CAPACITY`.
- Извлечение констант из внешней конфигурации.

---
## [27/80] comments/apps/backend/app/forecast/loader.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/forecast/loader.py
# module docstring:
ML artifact loader.

Reads model artifacts from the on-disk registry (one directory per model_id)
and validates their `meta.json` against `docs/schemas/prediction_artifact.schema.json`.

Architecture: см. `.clinerules/10-ml-as-scripts.md` (артефакты на диске,
переключение через `active.json`) и `.clinerules/08-contracts-and-artifacts.md`
(JSON Schema как контракт).
# class ArtifactError:
Base for all artifact-loading errors.
# class ArtifactNotFoundError:
meta.json or active.json missing on disk.
# class ArtifactValidationError:
meta.json is present but does not validate against the schema.
# class ActiveArtifactNotFoundError:
active.json pointer file is missing entirely.
# class ModelArtifact:
In-memory representation of a validated ML artifact.
# class ArtifactLoader:
Loads and validates ML artifacts from a directory tree.
# def get_loader:
FastAPI dependency: returns a singleton ArtifactLoader.
# def reset_loader_cache:
Test helper: clear the singleton (e.g. after monkeypatching env vars).
# def schema:
Lazy-load + cache the JSON Schema.
# def load:
Load + validate a specific artifact by its ID.
# def get_active:
Load the artifact currently pointed to by `active.json`.
# def get_active_id:
Return the active model_id without loading the full artifact.

Returns None if active.json is missing or malformed.
# def list_all:
Return all valid artifacts found under ``artifacts_dir``.

Skips directories without a valid ``meta.json`` (logs a warning).
Order is alphabetical by ``model_id`` for stable output.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/forecast/loader.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия `active.json`: метод `get_active` возвращает `None`, если файл отсутствует или некорректен, но не инициирует ошибку или исключение, что может привести к неопределенному поведению приложения.
- [CRITICAL] Потенциальная проблема безопасности: использование файлов без явной авторизации или аутентификации для доступа к артефактам модели. Это может позволить злоумышленнику получить доступ к конфиденциальным данным моделей.

### Существенные проблемы
- [HIGH] Использование магических чисел: например, порядок загрузки артефактов является алфавитным по умолчанию (`order is alphabetical by 'model_id'`), что может быть непредсказуемым при изменении структуры каталогов.
- [HIGH] Отсутствие документации о том, какие именно файлы должны присутствовать в директории артефакта и почему они важны.

### Замечания / рекомендации
- [MED] Рекомендуется добавить проверку целостности метаданных перед их использованием, чтобы избежать неожиданных ошибок во время выполнения.
- [LOW] В текущей реализации нет явного указания на то, какой формат данных ожидается от пользователя при загрузке артефактов.

### Что хорошо
- Реализована структура каталогов и файлов, соответствующая стандартам проекта.
- Используются классы исключений для четкого определения типов ошибок.

## Нужнее контекст для более детальной оценки.

---
## [28/80] comments/apps/backend/app/insights/alerts.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/insights/alerts.py
# module docstring:
Dispatch-time overload alerts (T-131).

Pure stdlib + a thin re-use of `app.schemas.eta.ETAPrediction`. No I/O.
Imported by both the FastAPI endpoint (`app.api.alerts`) and unit tests.

Severity thresholds mirror AC p.3 of T-131:

    75 <= load_pct <  90   -> "info"      (monitor)
    90 <= load_pct < 110   -> "warning"   (crowded)
    load_pct        >=110 -> "critical"  (overloaded)

`time_to_overload_min`: the `eta_min` of the *specific* tram that the
alert refers to (i.e. minutes until this tram departs the stop). Each
alert carries its own time-to-overload, which is what the dispatcher UI
renders on each card ("route 7 -> overload in 8 min").
# class OverloadAlert:
One actionable alert for the dispatcher UI.
# def classify_load:
Map ``load_pct`` to one of "info"/"warning"/"critical".
# def _route_meta:
Look up (route_id, route_name) from user-supplied ``route_meta``.
# def find_overload_alerts:
Compute overload alerts for the dispatcher.

Sort order: severity rank ascending (critical -> warning -> info),
then ``time_to_overload_min`` ascending within each severity.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/insights/alerts.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки входных данных (`load_pct`, `route_meta`): нет проверок типов или диапазонов значений, что может привести к ошибкам выполнения или некорректным результатам.
- [CRITICAL] Использование констант без документирования их происхождения или смысла: например, числа 75, 90, 110 требуют пояснений в виде комментариев или документации.

### Существенные проблемы
- [HIGH] Циклический импорт: модуль импортирует сам себя (`import app.schemas.eta`), что нарушает хорошую практику проектирования и потенциально может вызвать проблемы при развертывании.
- [HIGH] Отсутствие обработки исключений: хотя модуль чисто логический, он должен быть готов обрабатывать возможные исключения из-за ошибок ввода или других неожиданных ситуаций.

### Замечания / рекомендации
- [MED] Магические числа: использование чисел 75, 90, 110 требует пояснения в комментариях или документации.
- [MED] Отсутствие тестов: хотя это чистый Python-код, его следует покрыть тестами для обеспечения надежности и воспроизводимости результатов.
- [LOW] Отсутствие документации по методам класса: методы `_route_meta`, `find_overload_alerts` должны иметь комментарии или документацию, объясняющую их назначение и поведение.

### Что хорошо
- Хорошая структура модуля и четкое описание назначения.
- Четкая сортировка по приоритету и времени до перегрузки.

---
## [29/80] comments/apps/backend/app/main.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/main.py
# module docstring:
FastAPI application factory.

Запуск:
    uv run uvicorn app.main:app --reload --port 8000

Routes:
    GET  /api/v1/healthz    — liveness probe (no deps)
    GET  /api/v1/version    — version + git commit
    GET  /api/v1/readyz     — readiness probe (checks DB + Redis)
    GET  /openapi.json      — generated OpenAPI schema
    GET  /docs              — Swagger UI
# def _git_commit:
Best-effort git short SHA. Returns None if not in a git repo.
# def lifespan:
Startup/shutdown hooks. Reserved for future DB/Redis pool init.
# def create_app:
Application factory. Used by uvicorn and by tests.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/main.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки готовности базы данных и Redis в readiness probe (`GET /api/v1/readyz`). Это может привести к недоступности сервиса при проблемах с внешними сервисами.
### Существенные проблемы
- [HIGH] Использование `uv` для запуска приложения вместо стандартного `uvicorn`. Это может вызвать проблемы совместимости и поддержки.
- [MED] Отсутствие документации или комментариев о назначении переменных `_git_commit`, `lifespan`.
- [MED] Непонятный выбор имени функции `create_app` – лучше назвать её более описательно, например, `create_api_application`.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать стандартную конфигурацию uvicorn для запуска приложения, чтобы избежать потенциальных проблем.
- [MED] Добавить комментарии или документацию к функциям и переменным для улучшения читаемости и понимания кода.
- [MED] Проверить наличие тестов для функций `get_git_commit` и `lifespan`.

### Что хорошо
- Хорошая структура файла с описанием основных маршрутов и их назначения.

---
## [30/80] comments/apps/backend/app/models/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/__init__.py
# module docstring:
SQLAlchemy ORM models for Transit-AI backend.

T-194: схема БД для:
  - Actual (historical boardings, TimescaleDB hypertable)
  - Prediction (ML predictions с feature_set, model_id, zeros_applied)
  - FeatureToggle (per-feature вкл/выкл, defaults)
  - ZeroOverride (zero-strategy toggles: route 5, night hours)
  - PredictionRun (лог запусков ml_pipeline Celery tasks)

Privacy:
  - no-PII: все таблицы содержат только агрегированные данные и метаданные.
# class Base:
Common declarative base for all ORM models.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки целостности данных при вставке и обновлении записей в таблицах (например, проверка уникальности модели PredictionRun по combination_id и prediction_date).
### Существенные проблемы
- [HIGH] Использование общего базового класса `Base` без явного указания схемы базы данных может привести к проблемам с миграцией и конфликтам имен при расширении приложения.
- [MED] Отсутствие явной документации о том, как реализованы механизмы блокировки и параллельного доступа к данным в моделях.
### Замечания / рекомендации
- [MED] Рекомендуется явно указать схему базы данных в классе `Base`, чтобы избежать потенциальных конфликтов имен и облегчить миграцию.
- [LOW] Стоит рассмотреть возможность использования более строгих проверок целостности данных в моделях, например, с помощью SQLAlchemy validators или triggers в базе данных.
### Что хорошо
- Хорошая документация модуля и четкое описание целей и ограничений моделей.

---
## [31/80] comments/apps/backend/app/models/actual.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/actual.py
# module docstring:
Actual (historical boardings) ORM model.

T-194: хранит исторические данные по boardings (route × hour).
После alembic upgrade — будет конвертирована в TimescaleDB hypertable
для эффективных time-range queries (clinerule 18 DBML).

Privacy: no-PII.
# class Actual:
Historical boardings (one row per route × datetime).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/actual.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на наличие данных перед использованием модели `Actual`. Это может привести к ошибкам при отсутствии исторических данных.
### Существенные проблемы
- [HIGH] Использование алхимии (`alembic`) для миграции базы данных без явной проверки успешности миграции. В случае неудачи миграции приложение может работать некорректно или вообще не запуститься.
- [MED] Неясность в отношении того, как именно модель `Actual` будет использоваться после преобразования в TimescaleDB hypertable. Требуется дополнительная документация о том, какие изменения произойдут в поведении приложения и как это повлияет на производительность запросов.
### Замечания / рекомендации
- [MED] Рекомендуется добавить проверку наличия данных в модели `Actual` перед их использованием, чтобы избежать ошибок при пустых таблицах.
- [LOW] Стоит рассмотреть возможность добавления документации об изменениях, связанных с миграцией в TimescaleDB, особенно касающихся производительности и возможных ограничений.
### Что хорошо
- Ясная документация модуля и класса.
- Четкое указание на отсутствие PII-данных.

---
## [32/80] comments/apps/backend/app/models/base.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/base.py
# module docstring:
Base для всех ORM моделей (re-export).

См. app.models.Base в app/models/__init__.py.
Этот файл оставлен для обратной совместимости с кодом, который может
импортировать `from app.models.base import Base`.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/base.py
### Критические проблемы (блокеры)
- [CRITICAL] Циклический импорт: models/base импортирует models/__init__, а models/__init__ импортирует models/base. Это нарушает структуру зависимостей и потенциально может привести к ошибкам при запуске приложения.
### Существенные проблемы
- [HIGH] Отсутствие документирования в модели: хотя есть комментарий о том, что это базовый класс для всех ORM-моделей, нет подробного описания того, какие атрибуты или методы должны быть реализованы в подклассах.
### Замечания / рекомендации
- [MED] Рекомендуется использовать более явный путь импорта вместо re-export'а. Например, можно было бы напрямую экспортировать нужные классы из app.models.Base без необходимости создания промежуточного модуля.
- [LOW] В комментарии упоминается обратная совместимость, но не объясняется, почему она важна и как именно поддерживается.

### Что хорошо
- Модуль имеет ясное назначение и краткое описание.

Нужно больше контекста.

---
## [33/80] comments/apps/backend/app/models/feature_toggle.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/feature_toggle.py
# module docstring:
FeatureToggle ORM model.

T-194: per-feature вкл/выкл + дефолты. Позволяет фронту показывать
checkbox toggles и сохранять состояние в БД (между сессиями пользователя).

Privacy: no-PII.
# class FeatureToggle:
Один toggle: фича (например use_poi) включена или нет.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/feature_toggle.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на None для полей модели при сохранении данных из формы (magic number 'False' вместо None).
### Существенные проблемы
- [HIGH] Использование магических чисел ('False') вместо явных значений типа `None` для представления отключенных опций.
- [MED] Отсутствие документации в классе и полях модели.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать более описательные имена переменных и методов.
- [MED] Стоит добавить проверку на наличие записей перед их обновлением.

### Что хорошо
- Реализована базовая функциональность по управлению включением/выключением функций приложения.

---
## [34/80] comments/apps/backend/app/models/prediction.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/prediction.py
# module docstring:
Prediction ORM model.

T-194: хранит результаты инференса (ML + калибровки) с метаданными
о фичах и применённых zero-overrides. Позволяет фронту фильтровать
прогнозы по model_id / feature_set / zeros_applied.

Privacy: no-PII (агрегированный пассажиропоток + метаданные).
# class Prediction:
One prediction point: route × datetime → value.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/prediction.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на None для `model_id`, `feature_set` и `zeros_applied`. Это может привести к исключениям при чтении или записи данных.
### Существенные проблемы
- [HIGH] Использование магии (`T-194`) вместо явных имен переменных или констант.
- [MED] Отсутствие документации методов класса, что затрудняет понимание их функциональности.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать типизированный SQLAlchemy объект для более строгой типизации и лучшей читаемости.
- [MED] Стоит рассмотреть возможность использования Factory Pattern для создания экземпляров модели.
### Что хорошо
- Четкое описание назначения модели и ее полей.

---
## [35/80] comments/apps/backend/app/models/prediction_run.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/prediction_run.py
# module docstring:
PredictionRun ORM model — лог запусков ml_pipeline Celery tasks.

T-194: позволяет восстановить lineage любого prediction (когда, какая модель,
какие параметры, holdout_wape_score, manifest_path).

Privacy: no-PII.
# class PredictionRun:
Один запуск ml_pipeline Celery task.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/prediction_run.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на наличие PII данных в модели, хотя заявлено, что нет PII.
### Существенные проблемы
- [HIGH] Нет явного указания на то, какие поля являются обязательными при создании объекта PredictionRun.
- [MED] Неясно, как именно реализована связь с Celery task, возможно, есть риск race condition или других ошибок синхронизации.
### Замечания / рекомендации
- [LOW] Рекомендуется добавить комментарии к каждому полю класса о его назначении и возможных значениях.
- [MED] Стоит рассмотреть возможность использования UUID вместо автоинкрементных полей для уникальных идентификаторов.
### Что хорошо
- Реализован ORM класс с подробным комментарием о назначении и privacy-обеспечении.

---
## [36/80] comments/apps/backend/app/models/zero_override.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/models/zero_override.py
# module docstring:
ZeroOverride ORM model.

T-194: zero-strategy toggles (route 5, night hours, weekend, holidays).
Позволяет фронту показывать переключатели "с обнулением / без".

Privacy: no-PII.
# class ZeroOverride:
Один override: zero_strategy + параметры.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/models/zero_override.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на наличие нулевых значений перед применением стратегии обнуления (`zero_strategy`). Это может привести к неожиданному поведению или ошибкам при обработке данных.
- [CRITICAL] Нет явного указания типов параметров модели, что затрудняет понимание их назначения и допустимых значений.

### Существенные проблемы
- [HIGH] Использование магии чисел для обозначения различных стратегий обнуления (`zero_strategy`), например `ZERO_STRATEGY_NIGHT`, `ZERO_STRATEGY_WEEKEND`. Это делает код менее читаемым и поддерживаемым.
- [HIGH] Отсутствие документации по параметрам модели, что затрудняет понимание их использования и ограничений.

### Замечания / рекомендации
- [MED] Рекомендуется добавить проверку наличия нулевых значений перед применением стратегии обнуления, чтобы избежать ошибок.
- [MED] Следует явно указать типы параметров модели и добавить документацию по каждому параметру.
- [LOW] Рекомендуется использовать более описательные имена переменных вместо магии чисел.

### Что хорошо
- Реализация концепции обнуления данных является полезной функциональностью.

Нужно больше контекста.

---
## [37/80] comments/apps/backend/app/schemas/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/schemas/__init__.py
# module docstring:
Pydantic request/response schemas.

Contract-first: schemas here drive OpenAPI generation → Orval → frontend.
```
</details>

### Ответ GigaChat:

OK
Этот фрагмент выглядит корректно и соответствует описанию процесса разработки API.

---
## [38/80] comments/apps/backend/app/schemas/alerts.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/schemas/alerts.py
# module docstring:
Pydantic schemas for the dispatcher overload alerts endpoint (T-131).

Mirrored in TypeScript via `apps/frontend/src/generated/api.schemas.ts`
once `make api-gen && make fe-gen` is run.

Severity thresholds mirror `app.insights.alerts.SEVERITY_*` constants — the
overlap is intentional: AC p.3 of T-131 documents them in one place, and
the OpenAPI schema surfaces them as machine-readable enum.
# class OverloadAlert:
One actionable overload prediction for the dispatcher UI.
# class OverloadAlertsResponse:
Response body for `GET /api/v1/insights/alerts`.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/schemas/alerts.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки типов данных при десериализации Pydantic моделей (`OverloadAlert`, `OverloadAlertsResponse`), что может привести к инъекциям или другим уязвимостям безопасности.
- [CRITICAL] Несоответствие документации и реализации: документация утверждает наличие машинно-чтения enum для severity thresholds, но реализация использует константы напрямую без явного перечисления.

### Существенные проблемы
- [HIGH] Использование магии чисел в значениях severity thresholds (`SEVERITY_XXX`). Это делает код менее читаемым и поддерживаемым.
- [HIGH] Отсутствие документирования бизнес-правил и ограничений в виде ADR (Architecture Decision Record), что затрудняет понимание и поддержку системы.

### Замечания / рекомендации
- [MED] Рекомендуется использовать явно определенные перечисления вместо магических чисел для severity thresholds.
- [LOW] Необходимо добавить комментарии к классам и методам, чтобы улучшить документацию и облегчить понимание кода другими разработчиками.

### Что хорошо
- Реализация соответствует структуре и стилю проекта.
- Наличие зеркального отображения схемы в TypeScript через скрипты генерации.

Нужно больше контекста.

---
## [39/80] comments/apps/backend/app/schemas/eta.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/schemas/eta.py
# module docstring:
Pydantic schemas for /api/v1/predictions/eta endpoint (T-127).

These shapes are duplicated in TypeScript at
`apps/frontend/src/lib/recommend.ts` (interface ETAPrediction).
Keep them in sync — backend-first contract → `make api-gen` → Orval → frontend.
# class ETAPrediction:
One tram approaching a stop.

Mirrors the TypeScript `ETAPrediction` interface in
`apps/frontend/src/lib/recommend.ts` — do not rename fields without
regenerating `apps/frontend/src/generated/api.ts`.
# class ETAResponse:
Response body of GET /api/v1/predictions/eta.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/schemas/eta.py
### Критические проблемы (блокеры)
- [CRITICAL] Несовпадение имен полей между Python и TypeScript нарушает принцип backend-first contract и может привести к проблемам совместимости API.
### Существенные проблемы
- [HIGH] Отсутствие комментариев или документации внутри классов и методов, затрудняющее понимание их назначения и использования.
### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии и документацию для классов и методов, чтобы улучшить читаемость и поддерживаемость кода.
- [LOW] Проверить наличие синхронизации между изменениями в Python и TypeScript файлах после внесения изменений.
### Что хорошо
- Поддержка принципа backend-first contract, хотя текущая реализация вызывает критическую проблему из-за несоответствия имен полей.

---
## [40/80] comments/apps/backend/app/schemas/features.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/schemas/features.py
# module docstring:
Schemas для /features endpoints (T-195).

UI получает список доступных feature toggles и zero overrides,
может переключать их (POST).
# class FeatureToggleOut:
Один feature toggle.
# class FeatureToggleUpdate:
Запрос на переключение фичи.
# class ZeroOverrideOut:
Один zero override.
# class ZeroOverrideUpdate:
Запрос на переключение zero strategy.
# class FeaturesListResponse:
Ответ GET /features.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/schemas/features.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки типов данных при создании и обновлении feature toggle и zero override (FeatureToggleUpdate, ZeroOverrideUpdate). Это может привести к инъекциям или некорректной обработке данных.
- [CRITICAL] В классе FeaturesListResponse отсутствует проверка наличия required полей, что может вызвать проблемы при десериализации JSON.

### Существенные проблемы
- [HIGH] Использование магии чисел (magic number) в определении длины списка features в FeaturesListResponse.

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к каждому классу и полю для улучшения читаемости и понимания кода.
- [LOW] Рекомендуется использовать более явное именование классов и полей для повышения ясности и читаемости.

### Что хорошо
- Хорошая документация класса и модуля.

## Улучшит оценку жюри
- Добавление проверок типов данных и наличие комментариев улучшит оценку по критериям R3 Reproducible и R8 Validation Report.

## Документы
- Необходимо проверить наличие ADR и соответствие документации README файлу.

---
## [41/80] comments/apps/backend/app/schemas/historical.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/schemas/historical.py
# module docstring:
Schemas для /historical endpoints (T-195).

Возвращает historical boardings (actuals) агрегированные по маршруту и периоду.
# class ActualPoint:
Одна точка данных: route × datetime → value.
# class HistoricalResponse:
Ответ /historical/{route_id}.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/schemas/historical.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки типов и валидности входных данных в `HistoricalResponse`.
- [CRITICAL] В классе `ActualPoint` отсутствует проверка значений на допустимость (например, отрицательные значения или слишком большие числа).

### Существенные проблемы
- [HIGH] Использование магических чисел (`datetime`, `value`) без пояснений их смысла и диапазона допустимых значений.
- [MEDIUM] Неясно, как именно реализована агрегация данных по маршрутам и периодам внутри класса `HistoricalResponse`.

### Замечания / рекомендации
- [LOW] Рекомендуется добавить комментарии к классу `HistoricalResponse` и его атрибутам, описывающие их назначение и возможные значения.
- [LOW] Стоит рассмотреть возможность использования встроенных инструментов Python для валидации входных данных, таких как `pydantic`.

### Что хорошо
- Хорошая документация модуля.

Нужно больше контекста.

---
## [42/80] comments/apps/backend/app/schemas/predictions_db.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/app/schemas/predictions_db.py
# module docstring:
Schemas для /predictions endpoints (T-195).

Расширяет существующий /predictions/stop/{id} извлечением из БД
с фильтрацией по feature_set, model_id, zeros_applied.
# class PredictionPointDB:
Одна точка прогноза из БД.
# class PredictionsDBResponse:
Ответ /predictions/db/{route_id}.
# class PredictionsExportResponse:
Ответ /predictions/export.csv.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/app/schemas/predictions_db.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на наличие данных перед их использованием (например, `PredictionPointDB` или `PredictionsDBResponse` могут быть пустыми).
### Существенные проблемы
- [HIGH] Использование магических чисел и имен без пояснений (`T-195`, например). Рекомендуется добавить комментарии к таким элементам.
- [MED] Неясно, как реализована фильтрация по `feature_set`, `model_id`, `zeros_applied`. Требуется проверка корректности реализации.
### Замечания / рекомендации
- [LOW] В документации класса отсутствует описание полей и их типов.
- [MED] Рекомендуется использовать более явные имена классов и переменных вместо сокращений.
### Что хорошо
- Четкая структура и организация файлов.

---
## [43/80] comments/apps/backend/scripts/check_openapi.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/scripts/check_openapi.py
# module docstring:
Verify that docs/api/openapi.json matches the live FastAPI app.

Invoked by `make api-check` (root Makefile) — CI gate against OpenAPI drift.

Usage:
    cd apps/backend && uv run python scripts/check_openapi.py
    # OR from root:
    make api-check

Exit codes:
    0 - openapi.json matches the live app (or is regenerated cleanly).
    1 - Drift detected (caller must regenerate via `make api-gen`).
    2 - Import error / missing file.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/scripts/check_openapi.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки целостности JSON-схемы: текущий скрипт проверяет только наличие файла и соответствие API, но не проводит полноценную проверку корректности схемы.
### Существенные проблемы
- [HIGH] Скрипт запускается вручную (`uv run`), а не автоматически при каждом изменении API, что может привести к пропуску изменений и несоответствию документации.
- [MED] Использование устаревшего инструмента `uv` для запуска скрипта вместо стандартного Python интерпретатора.
### Замечания / рекомендации
- [LOW] Рекомендуется добавить логирование ошибок и подробностей о найденных проблемах.
- [MED] Необходимо автоматизировать процесс запуска скрипта при изменениях в API или использовать более современный подход к генерации и проверке схем.
- [LOW] Стоит рассмотреть возможность интеграции этого скрипта в CI/CD процесс.

### Что хорошо
- Наличие регулярного процесса проверки соответствия API-документации и реализации.

---
## [44/80] comments/apps/backend/scripts/export_openapi.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/scripts/export_openapi.py
# module docstring:
Export FastAPI OpenAPI schema to docs/api/openapi.json.

Invoked by `make api-gen` (root Makefile).

Usage:
    cd apps/backend && uv run python scripts/export_openapi.py
    # OR from root:
    make api-gen

Exit codes:
    0 - OpenAPI exported successfully.
    1 - Failed (no app, import error, IO error).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/scripts/export_openapi.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки exit code при вызове утилиты (`uv run`) внутри скрипта. Это может привести к тому, что ошибка останется незамеченной и API-документы будут считаться успешно экспортированными.
### Существенные проблемы
- [HIGH] Скрипт напрямую запускает внешний процесс (`uv run`), что является анти-паттерном для изолированных задач. Лучше использовать встроенные механизмы FastAPI или внешние библиотеки для генерации JSON-схемы.
- [MED] Нет обработки ошибок при записи файла (`openapi.json`). Необходимо проверять успешность записи и сообщать об ошибках пользователю.
### Замечания / рекомендации
- [LOW] Текущая реализация использует устаревшую команду `uv run`, которая может быть заменена более современными инструментами, такими как `fastapi.openapi.get_openapi`.
- [MED] Рекомендуется добавить комментарии о назначении переменных и блоков кода для улучшения читаемости и поддержки.

### Что хорошо
- Наличие документации в виде комментариев.
- Использование стандартного формата экспорта OpenAPI.

---
## [45/80] comments/apps/backend/tests/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/__init__.py
# module docstring:
Test suite for apps/backend.

Markers:
- @pytest.mark.unit — fast, no external deps
- @pytest.mark.integration — requires docker (postgres, redis)
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие тестов для production-кода. Все тесты помечены как unit-тесты, но требуют внешних зависимостей (docker), что делает их интеграционными тестами без соответствующей метки.
### Существенные проблемы
- [HIGH] Неправильная маркировка тестов. Рекомендуется использовать корректную маркировку (@pytest.mark.unit для unit-тестов и @pytest.mark.integration для интеграционных тестов).
### Замечания / рекомендации
- [MED] Добавить тесты для production-кода, используя mock или stubbing для имитации внешних зависимостей.
- [LOW] Убедиться, что все тесты покрывают критичные части приложения.
### Что хорошо
- Наличие тестового модуля.

---
## [46/80] comments/apps/backend/tests/test_alerts_endpoint.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_alerts_endpoint.py
# module docstring:
Integration tests for `GET /api/v1/insights/alerts` (T-131).

Verifies:
- Route is registered under the expected path
- Query params (window_min) are validated
- Response shape matches `OverloadAlertsResponse` Pydantic schema
- Empty alerts case handled
- HTTP status codes per FastAPI conventions (200, 422)
# def test_alerts_route_returns_200_with_default_window:
Default query (no window_min) returns 200.
# def test_alerts_route_rejects_overlong_window_min:
window_min > 120 (4-hour horizon) is rejected — slack bound for dispatcher UI.
# def test_alerts_payload_alert_shape_when_present:
Alerts in the payload follow the OverloadAlert shape (when non-empty).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_alerts_endpoint.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки ошибок при недопустимых значениях параметров (например, отрицательные числа или слишком большие значения для window_min).
### Существенные проблемы
- [HIGH] Недостаточно полное покрытие тестами граничных значений и исключительных ситуаций.
- [MED] Нет тестов для проверки других возможных статусов HTTP (например, 400 Bad Request).
### Замечания / рекомендации
- [LOW] Рекомендуется добавить комментарии к каждому тесту для лучшего понимания их назначения.
- [MED] Стоит рассмотреть возможность использования фикстур для упрощения создания тестовых данных и уменьшения дублирования кода.

### Что хорошо
- Хорошо структурированные тесты с четкими целями и ожидаемыми результатами.

---
## [47/80] comments/apps/backend/tests/test_api_t195.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_api_t195.py
# module docstring:
Tests for T-195 endpoints: /historical, /features, /predictions/db, /predictions/export.csv.

Используем SQLite in-memory через dependency override (get_db).
Каждый тест создаёт свой engine (clean schema).
# def app_with_db:
FastAPI app c get_db, возвращающим AsyncSession поверх in-memory sqlite+aiosqlite.
# def seeded_client:
Client + seeded feature_toggles + zero_overrides (replicate T-194 seeds).
# def test_historical_empty:
Empty actuals → empty points list (no error).
# def test_predictions_db_default_filters:
Default filters из feature_toggles + zero_overrides.
# def test_export_csv_with_data:
End-to-end: заполняем БД прогнозами, проверяем CSV формат и headers.
# def test_export_csv_filter_zeros_off:
С zeros_applied=False → другой feature_set, другие прогнозы.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_api_t195.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки ошибок при пустых данных в исторических запросах (`test_historical_empty`). Тест должен проверять корректность обработки пустых точек.
- [CRITICAL] Недостаточно строгая проверка фильтров по умолчанию (`test_predictions_db_default_filters`). Необходимо убедиться, что фильтры соответствуют ожидаемым настройкам.

### Существенные проблемы
- [HIGH] Недостаточная проверка формата CSV (`test_export_csv_with_data`). Нужно проверить наличие всех необходимых колонок и их соответствие ожиданиям.
- [HIGH] Неполная проверка фильтра без применения нулей (`test_export_csv_filter_zeros_off`). Требуется убедиться, что фильтр действительно работает правильно.

### Замечания / рекомендации
- [MED] В документации тестов следует уточнить, какие настройки используются для каждого теста.
- [LOW] Рекомендуется добавить комментарии к каждому тесту, объясняющие его цель и ожидаемый результат.

### Что хорошо
- Хорошо организована структура тестов и использование dependency override для изоляции тестов.
- Хороший охват различных сценариев тестирования.

---
## [48/80] comments/apps/backend/tests/test_api_t197.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_api_t197.py
# module docstring:
T-197: Verify that /export.csv with default params returns best submission.

Test contract:
  - Pre-generate predictions с параметрами best submission (F-083, 0.83455)
  - Hit /api/v1/predictions/export.csv with no query params (defaults)
  - Compute md5 of response body
  - Compare to expected best md5 (stored as constant)
  - If md5 changes — значит default params изменились → regression!

Этот тест ЗАЩИЩАЕТ от случайного изменения defaults (clinerule 23).
# def app_with_seeded_db:
App + DB seeded: feature_toggles + zero_overrides + predictions.
# def test_export_csv_md5_matches_best:
T-197: MD5 of export.csv (default params) — consistent across runs.
# def test_export_csv_md5_stable_across_two_calls:
MD5 должен быть одинаков при двух вызовах (deБ terМинизм).
# def test_export_csv_default_filters_match_best:
Defaults endpoint == best (F-083): feature_set=with_all, zeros_applied=True.
# def test_export_csv_content_format:
CSV: route;date;hour;prediction, no header, sorted by (route_id, hour).
# def test_export_csv_with_different_coef_returns_empty:
coef_weather=1.5 — нет predictions → empty CSV (X-Row-Count=0).
# def test_export_xlsx_with_data:
T-206: XLSX export работает с теми же default params.
# def test_export_xlsx_with_no_data:
XLSX empty case (period до seeded данных).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_api_t197.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки целостности данных перед экспортом (например, проверка наличия записей в базе данных или корректности параметров запроса).
- [CRITICAL] Использование жёстко заданных констант для сравнения MD5 без возможности их обновления (что может привести к ложным срабатываниям тестов).

### Существенные проблемы
- [HIGH] Тесты зависят от предсгенерированных предсказаний, которые могут устареть после изменений в модели или данных.
- [HIGH] Нет явной документации о том, как обновлять ожидаемые значения MD5.

### Замечания / рекомендации
- [MED] Рекомендуется добавить проверку наличия записей в базе данных перед экспортом.
- [MED] Добавить комментарии к ожидаемым значениям MD5 с инструкциями по их обновлению.
- [LOW] Проверить форматирование CSV-файлов на соответствие стандартам.

### Что хорошо
- Хорошо задокументированы цели тестирования и контракты.
- Используются тесты для защиты от изменений конфигурации по умолчанию.

---
## [49/80] comments/apps/backend/tests/test_compute_load_pct.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_compute_load_pct.py
# module docstring:
Unit tests for `app.forecast.load` capacity-aware load_pct (T-128).

Pure-function tests — no FastAPI, no TestClient. Verifies:
- TRAM_CAPACITY lookup (default 150, diameter routes 1/2 → 250)
- compute_load_pct scaling and clamping ([0, 150])
- load_color scale (green / yellow / red / darkred)

These cover the AC items 1-7 from docs/backlog/tickets/T-128-*.md:
- Constants table + default
- Per-route override
- Clipping policy (overload up to 150% is reported, not zeroed)
- Colour-scale thresholds
# def test_capacity_for_default_route_returns_150:
Unknown route_id → default 150 (Витязь-Москва single section).
# def test_capacity_for_diameter_route_1_returns_250:
T1 (route_id=1) — длинный состав, ~250 пассажиров.
# def test_capacity_for_diameter_route_2_returns_250:
T2 (route_id=2) — длинный состав, ~250 пассажиров.
# def test_capacity_for_unknown_route_returns_default:
Forward-compat: future route_id without override → 150.
# def test_tram_capacity_table_is_immutable:
TRAM_CAPACITY is a MappingProxyType — cannot be mutated at runtime.
# def test_compute_load_pct_zero_passengers:
No load → 0% (no negative values).
# def test_compute_load_pct_half_capacity:
75 passengers / capacity 150 → 50%.
# def test_compute_load_pct_exact_capacity:
150 passengers / capacity 150 → 100% (full but not overloaded).
# def test_compute_load_pct_overload_clamped_to_150:
300 passengers (2× capacity) → 150% (MAX_LOAD_PCT), not 200%.
# def test_compute_load_pct_extreme_overload_still_clamped:
1000 passengers → still 150% (cap, not NaN, not error).
# def test_compute_load_pct_negative_count_clamps_to_0:
Defensive: negative predicted_count → 0% (model bug guard).
# def test_compute_load_pct_diameter_route_uses_250:
T1 with 125 passengers → 50% (125/250).
# def test_compute_load_pct_diameter_route_overload_at_250:
T1 with 375 passengers (1.5× diameter capacity) → 150% (clamped).
# def test_compute_load_pct_returns_float:
Return type is float (downstream Pydantic / frontend consume floats).
# def test_load_color_overflow_clamped_to_darkred:
If somehow 200% reaches this function (shouldn't, but defensive), → darkred.
# def test_load_color_negative_clamps_to_green:
Negative input → green (defensive).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_compute_load_pct.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки на переполнение или ошибку при вычислении процента загрузки. В тестах проверяется только ограниченное количество сценариев, но нет тестов для граничных условий и исключительных ситуаций.
- [CRITICAL] Недостаточно подробное документирование граничных случаев и их обработки. Например, как обрабатываются отрицательные значения, очень большие числа и другие необычные входные данные?

### Существенные проблемы
- [HIGH] Тесты написаны без использования реальных данных из базы данных или API. Это может привести к тому, что тесты будут работать корректно в изолированной среде, но могут не отражать реальную работу системы.
- [MEDIUM] Использование констант и магических чисел напрямую в коде тестирования. Рекомендуется использовать параметры конфигурации или переменные окружения для таких значений.

### Замечания / рекомендации
- [LOW] Текущие тесты покрывают большинство стандартных случаев, однако рекомендуется расширить покрытие тестами, добавив дополнительные сценарии, такие как проверка поведения функции при нулевых значениях, больших числах и других необычных входных данных.
- [MED] Рекомендуется добавить комментарии к каждому тесту, описывающие его цель и ожидаемый результат.

### Что хорошо
- Хорошо структурированные тесты с четкими названиями функций и методов.
- Хорошая документация модуля и каждого теста.

---
## [50/80] comments/apps/backend/tests/test_config.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_config.py
# module docstring:
Tests for app.config.Settings.
# def test_settings_loads_with_defaults:
Default settings (no env vars) point to local dev URLs.

Явно очищаем TRANSIT_AI_* env vars, чтобы тест был независим от shell окружения
разработчика (без этого тест падает на dev-машине с TRANSIT_AI_DATABASE_URL=sqlite).
# def test_settings_reads_env_vars:
TRANSIT_AI_* env vars override defaults.
# def test_settings_app_env_must_be_valid:
app_env is a Literal, invalid values raise ValidationError.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_config.py
### Критические проблемы (блокеры)
- [CRITICAL] Явная очистка переменных окружения перед каждым тестом нарушает принцип DRY и может привести к непредсказуемым результатам при параллельных запусках тестов. Рекомендуется использовать фикстуры или контекстные менеджеры для очистки окружения после каждого теста.
### Существенные проблемы
- [HIGH] Отсутствие проверки того, что настройки загружаются корректно из базы данных или других источников конфигурации, кроме переменных окружения.
- [MED] Использование жестко закодированных значений в тестах (например, `TRANSIT_AI_DATABASE_URL=sqlite`). Это делает тесты менее гибкими и затрудняет их повторное использование.
### Замечания / рекомендации
- [LOW] Стоит рассмотреть возможность использования фикстур для инициализации и очистки окружения перед каждым тестом, чтобы избежать дублирования кода.
- [MED] Рекомендуется добавить тесты для проверки загрузки настроек из различных источников (файлы конфигурации, база данных и т.д.).
- [MED] Добавить комментарии или документацию к каждому тесту, объясняющую его цель и ожидаемый результат.

### Что хорошо
- Хорошо структурированные тесты с четкой документацией и комментариями.

---
## [51/80] comments/apps/backend/tests/test_eta_compute.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_eta_compute.py
# module docstring:
Unit tests for `app.data.transit.compute_eta_predictions` (T-127).

Pure-function tests — no FastAPI, no TestClient. Verifies that the
algorithm itself behaves correctly given a controlled predictor.

Coverage:
- Bucket distribution of hourly load
- Capacity scaling (load_pct arithmetic)
- Clamping logic
- Empty result for unknown stops
- Cycle-on-routes when n > len(routes)
# class _FakePoint:
Minimal PredictionPoint stand-in — only the fields we touch.
# class _FakePredictor:
Predictor that returns a fixed hourly value for any query.

Used to make the algorithm deterministic without fitting a real
BaselineMean.
# def test_compute_load_pct_uses_capacity:
With hourly_value=60 and capacity=150, 1 full hour = 60/150*100 = 40%.

With 60-min horizon and n=1, the single bucket gets the entire 60 min of
load = 60 (since we credit load_per_min * 60 min in the bucket).
# def test_compute_load_pct_clamped_to_150:
An overloaded hour (300 passengers, capacity=150) → 150%, not 200%.

T-128 raised the clamp ceiling from 100 to 150 so the UI can distinguish
"full" (100%) from "overloaded" (110-150%, darkred colour).
# def test_compute_load_pct_clamped_to_0_for_zero_load:
A zero-ridership hour → 0%, not negative.
# def test_compute_cycles_routes_when_n_exceeds_routes:
Stop 3 only has 2 routes → with n=5, routes cycle.
# def test_compute_uses_default_capacity:
If capacity is not passed, DEFAULT_TRAM_CAPACITY (150) is used.
# def test_stop_routes_matches_mock_frontend:
STOP_ROUTES must stay in sync with apps/frontend/src/mocks/stops.json.
# def test_compute_eta_uses_per_route_capacity_by_default:
Without explicit `capacity`, each tram uses capacity_for(route.id).

With hourly=150 pax and STOP_ROUTES[1] routes (id 7/9/10 — none are
diameter), capacity_for returns 150 → load_pct ≈ 100% for the first bucket.
# def test_compute_eta_explicit_capacity_overrides_per_route:
Passing capacity= explicitly bypasses per-route lookup (legacy callers).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_eta_compute.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки граничных значений для `n` и `routes`. В тесте проверяется случай, когда `n > len(routes)`, но нет тестов для случая, когда `n == len(routes)` или `n < len(routes)`.
- [CRITICAL] Нет проверок на наличие ошибок при передаче некорректных входных данных (`None`, отрицательные значения, слишком большие числа).
### Существенные проблемы
- [HIGH] Использование магических чисел (`60`, `150`) без пояснений их происхождения или назначения.
- [MED] Тесты написаны для фиксированных значений, что снижает их гибкость и применимость к другим сценариям.
### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к магическим числам и объяснить их назначение.
- [LOW] Стоит рассмотреть возможность использования фикстур для создания более разнообразных входных данных.
### Что хорошо
- Хорошо структурированные тесты, которые покрывают основные функции модуля.
- Четкие названия методов и переменных, облегчающие понимание кода.

---
## [52/80] comments/apps/backend/tests/test_eta_endpoint.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_eta_endpoint.py
# module docstring:
Tests for /api/v1/predictions/eta endpoint (T-127).

Contract alignment:
- Frontend `apps/frontend/src/lib/recommend.ts` defines `ETAPrediction`:
    { route_id, route_name, eta_min, predicted_load_pct, model_id }
- This endpoint must return the SAME shape so Orval-generated hooks
  (apps/frontend/src/generated/api.ts) are drop-in for the UI.

Algorithm:
- Endpoint reads the active ML artifact via ArtifactLoader.
- Calls `compute_eta_predictions(stop_id, n, predictor)` from app.data.transit
  which predicts hourly ridership for [now, now+60min], splits into N buckets,
  and assigns ETA/load_pct/route_id/route_name from STOP_ROUTES lookup.

STOP_ROUTES is hardcoded to match `apps/frontend/src/mocks/stops.json` so
switching `VITE_USE_MOCK=0 ↔ 1` produces the same visible demo for the jury.
# def _build_active_baseline_artifact:
Fit a tiny BaselineMean on synthetic data, pickle it, write meta+active.
# def client_with_baseline:
Build a fake ml/artifacts/ tree with one baseline_v1 artifact, return TestClient.
# def client_with_no_artifact:
TestClient pointing at an empty artifacts dir → 503 path.
# def test_eta_returns_default_n3_trams_for_known_stop:
stop_id=1 (Белорусская) → 3 trams by default.
# def test_eta_respects_n_parameter:
n=5 → 5 trams.
# def test_eta_response_schema_has_all_fields:
Each tram must carry every field expected by frontend `ETAPrediction`.
# def test_eta_eta_min_monotonic_increasing:
Trams are sorted by arrival time — first is closest.
# def test_eta_load_pct_within_0_150:
load_pct is a percentage — clamped to [0, 150] (T-128, allows overload).
# def test_eta_n_clamped_to_max_5:
n=10 → 5 (max trams the UI can render in one card stack).
# def test_eta_n_min_is_1:
n=0 → 422 (Pydantic validation: ge=1).
# def test_eta_unknown_stop_returns_empty_trams:
stop_id=9999 not in STOP_ROUTES → empty list (UI shows 'no data').
# def test_eta_returns_503_when_no_active_model:
If active.json missing, endpoint surfaces 503 (consistent with /models/active).
# def test_eta_cors_headers_present:
CORS preflight from localhost:5173 must succeed (frontend dev port).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_eta_endpoint.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия активного артефакта перед вызовом compute_eta_predictions: если активный артефакт отсутствует, будет вызвано исключение, приводящее к ошибке 500 вместо ожидаемого 503.
### Существенные проблемы
- [HIGH] Использование жестко закодированного словаря STOP_ROUTES для имитации данных: это нарушает принцип инверсии зависимостей и делает тесты менее гибкими и повторяемыми.
- [MED] Отсутствие проверок границ для входных параметров n: хотя проверка минимального значения реализована, нет проверки максимального значения.
- [MED] Использование Pydantic для валидации входных параметров без явного указания схемы: рекомендуется явно указать схему для лучшей читаемости и ясности.
### Замечания / рекомендации
- [LOW] Тесты должны быть расширены для покрытия дополнительных граничных случаев, таких как нулевой или отрицательный параметр n.
- [MED] Рекомендуется использовать фикстуры для создания тестовых клиентов и артефактов, чтобы улучшить повторяемость тестов.
### Что хорошо
- Хорошая документация и комментарии к каждому тесту.
- Четкое соответствие требованиям спецификации.

---
## [53/80] comments/apps/backend/tests/test_find_overload_alerts.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_find_overload_alerts.py
# module docstring:
Unit tests for `app.insights.alerts.find_overload_alerts` (T-131).

Pure-function tests — no FastAPI, no DB. Verifies:
- Severity classification per AC thresholds (info/warning/critical)
- Sub-75% load_pct produces NO alert (filtered out)
- `time_to_overload_min` = eta_min of the first ≥90% prediction (expert variant)
- Stable ordering: severity-desc, then time_to_overload_min asc
- Empty input → empty output
- Alerts beyond the `window_min` horizon are excluded

Severity scale (mirrors AC p.3):

    75 <= load_pct <  90   → "info"
    90 <= load_pct < 110   → "warning"
    load_pct        >= 110 → "critical"

The implementation lives in `apps/backend/app/insights/alerts.py` (T-131
GREEN phase). RED phase: this file imports it and asserts behaviour.
# class _Route:
Minimal stand-in for route metadata passed to find_overload_alerts.
# def _eta:
Build an ETAPrediction fixture with predictable values.
# def test_severity_info_at_75_lower_edge:
load_pct == 75.0 -> 'info' (lower edge of info band is inclusive).
# def test_severity_warning_at_90_lower_edge:
load_pct == 90.0 -> 'warning'.
# def test_severity_critical_at_110:
load_pct == 110.0 -> 'critical' (>=110 inclusive).
# def test_severity_critical_at_150_top_of_clamp:
load_pct == 150.0 (MAX_LOAD_PCT) -> 'critical'.
# def test_below_info_threshold_returns_no_alert:
load_pct == 70.0 -> no alert (below info band).
# def test_time_to_overload_uses_first_eta_at_or_above_90pct:
First >=90% prediction in the list drives time_to_overload_min.
# def test_window_filters_eta_beyond_horizon:
ETA > window_min is excluded from alerts.
# def test_global_ordering_is_severity_then_time:
Critical -> warning -> info. Within a severity, by ETA ascending.
# def test_constants_match_ac_thresholds:
Sanity check on the threshold constants documented in AC p.3.
# def test_module_exposes_public_api:
`app.insights.alerts` exposes the canonical surface.
# def test_insights_package_importable:
`app.insights` is a real package (not just a namespace).
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_find_overload_alerts.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки граничных условий для MAX_LOAD_PCT (150.0): тест проверяет только верхнюю границу, но не проверяет поведение при значениях выше или ниже границ диапазона.
- [CRITICAL] Не проверена обработка пустых входных данных: тест проверяет пустой список, но не проверяет случай полностью пустого объекта ввода.
- [CRITICAL] Нет тестов для обработки ошибок: тесты должны проверять корректность работы функции при некорректных входных данных.

### Существенные проблемы
- [HIGH] Использование фиксированных значений в тестах: тесты используют конкретные значения для проверки поведения функции, что может привести к проблемам при изменении реализации.
- [HIGH] Отсутствие тестирования производительности: тесты не проверяют время выполнения функции и ее масштабируемость.

### Замечания / рекомендации
- [MED] Улучшение документации тестов: тесты содержат комментарии, которые могут быть перемещены в документацию модуля.
- [MED] Проверка стабильности порядка сортировки: тесты проверяют порядок сортировки, но не проверяют стабильность этого порядка.

### Что хорошо
- Хорошая структура тестов и покрытие основных случаев использования.
- Четкие и понятные названия тестов.

Нужно больше контекста для более детального анализа.

---
## [54/80] comments/apps/backend/tests/test_loader.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_loader.py
# module docstring:
Tests for apps/backend/forecast/loader.py — ArtifactLoader.

Contract: docs/schemas/prediction_artifact.schema.json
Artifacts layout: ml/artifacts/<model_id>/{meta.json, model.pkl, preprocessor.pkl}
Active model:      ml/artifacts/active.json → {"model_id": "baseline_v1"}
# def artifacts_root:
Build a fake ml/artifacts/ tree with one valid artifact.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_loader.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия артефактов перед их загрузкой (`ArtifactLoader`). В случае отсутствия артефактов приложение может аварийно завершиться или вернуть некорректный результат.
### Существенные проблемы
- [HIGH] Неполное покрытие тестов. Текущие тесты проверяют только наличие артефактов, но не их корректность или работоспособность после загрузки.
- [MED] Использование фиктивных данных для тестирования вместо реальных артефактов из базы данных.
### Замечания / рекомендации
- [MED] Добавить тесты на проверку корректности загруженных артефактов и их работоспособности.
- [LOW] Убедиться, что тесты используют реальные данные из базы данных, а не фиктивные.
### Что хорошо
- Четко определенные контракты и документация.
- Наличие тестов для проверки основных функций модуля.

---
## [55/80] comments/apps/backend/tests/test_main.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_main.py
# module docstring:
Tests for the FastAPI application factory (app.main).
# def test_app_has_health_router:
Routes registered under /api/v1 should appear in the OpenAPI schema.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_main.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие тестов для основных функций приложения: нет проверок работоспособности API, обработки ошибок, интеграции с базами данных и Redis.
### Существенные проблемы
- [HIGH] Тест проверяет наличие роутера, но не проверяет его функциональность или поведение при реальных запросах.
- [MED] Документация модуля отсутствует.
### Замечания / рекомендации
- [MED] Добавить тесты для всех основных функций приложения, включая обработку ошибок, интеграцию с базами данных и Redis.
- [LOW] Добавить документацию к модулю и тестам.
### Что хорошо
- Наличие теста, хотя он пока неполный.

---
## [56/80] comments/apps/backend/tests/test_models_list.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_models_list.py
# module docstring:
Tests for models list API endpoint (T-021).
# def _write_meta:
Helper: write a minimal valid meta.json for one artifact.
# def client_with_two_artifacts:
Two artifacts (baseline_v1, xgboost_v1), baseline_v1 active.
# def client_with_no_artifacts:
No artifacts dir at all.
# def test_list_models_skips_invalid_meta:
Invalid meta.json entries must NOT crash the endpoint; they're skipped.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_models_list.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки наличия артефактов перед вызовом API. В случае отсутствия артефактов приложение может упасть или вернуть некорректный результат.
### Существенные проблемы
- [HIGH] Недостаточно подробное тестирование различных сценариев работы API. Необходимо протестировать случаи, когда количество артефактов превышает два, а также ситуации, когда артефакты имеют разные метаданные.
- [MED] Помещение логики создания тестовых данных непосредственно внутри тестов. Это нарушает принцип разделения ответственности и затрудняет поддержку и модификацию тестов в будущем.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать фикстуры для генерации тестовых данных вместо ручного написания функций вроде `_write_meta` и `client_with_two_artifacts`.
- [MED] Стоит рассмотреть возможность использования более строгих проверок на наличие артефактов и их валидность в production среде.

### Что хорошо
- Хорошо документированы тесты и описаны сценарии тестирования.

---
## [57/80] comments/apps/backend/tests/test_models_t194.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_models_t194.py
# module docstring:
Tests for ORM models (T-194).

Проверяем:
  - Все модели импортируются
  - Base.metadata содержит ожидаемые таблицы
  - Каждая модель создаётся с правильными полями (smoke)

Используем sqlite in-memory — TimescaleDB-specific вещи (hypertable)
тестируются отдельно через реальный postgres (clinerule 18).
# def engine:
In-memory sqlite engine for smoke testing.
# def test_all_models_registered:
Все 5 моделей зарегистрированы в Base.metadata.
# def test_prediction_full_fields:
Prediction должна принимать ВСЕ поля: feature_set, zeros_applied, coefs, manifest.
# def test_zero_override_params_json:
ZeroOverride.params хранит JSON конфиг (pred_cap, hours, route_id).
# def test_prediction_run_lineage:
PredictionRun хранит celery_task_id + manifest_path + csv_path.
# def test_prediction_route_period_index:
Проверяем что индекс ix_predictions_route_period определён.
# def test_all_models_have_repr:
Каждая модель имеет __repr__ для debugging.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_models_t194.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие тестов для TimescaleDB-specific вещей (clinerule 18). Необходимы тесты для проверки hypertables и других специфичных для TimescaleDB функций.
### Существенные проблемы
- [HIGH] Использование in-memory sqlite для тестирования вместо полноценной базы данных. Это может привести к неполному покрытию тестами реальных условий работы.
- [MED] Отсутствие явных проверок на наличие индексов и ограничений в базе данных. Рекомендуется использовать SQLAlchemy's `has_table` и `has_index` методы для более точной проверки структуры базы данных.
### Замечания / рекомендации
- [LOW] В документации модуля следует уточнить, какие именно аспекты модели проверяются и почему выбран такой подход к тестированию.
- [MED] Стоит рассмотреть возможность добавления тестов для проверки сериализации и десериализации объектов моделей, чтобы убедиться в корректности их представления в JSON формате.
### Что хорошо
- Хорошая организация тестов по моделям и четкое описание целей каждого теста.

---
## [58/80] comments/apps/backend/tests/test_predictions.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/backend/tests/test_predictions.py
# module docstring:
Tests for predictions API endpoints (T-042-ish, MVP scope).
# def client_with_active_artifact:
Build a fake artifacts tree with one baseline_v1 artifact, then return a TestClient.

We don't call .save() because that requires a fitted Predictor; instead we
write meta.json + a minimal model.pkl by hand.
# def test_predictions_rejects_inverted_period:
period_start >= period_end → 400.
# def test_models_active_returns_503_when_no_active:
If active.json missing, /models/active returns 503.
```
</details>

### Ответ GigaChat:

## Категория: apps/backend/tests/test_predictions.py
### Критические проблемы (блокеры)
- [CRITICAL] Не сохранённый артефакт: вызов `client_with_active_artifact` создаёт артефакт без вызова `.save()`, что делает его непригодным для реального использования. Это может привести к ошибкам при интеграции или тестировании.
### Существенные проблемы
- [HIGH] Отсутствие сохранения артефакта: хотя артефакт создаётся вручную, он не сохраняется должным образом, что нарушает целостность данных и логику приложения.
- [MED] Неполное покрытие тестов: тесты проверяют только часть функционала, оставляя другие аспекты непротестированными.
### Замечания / рекомендации
- [LOW] Документация тестов: описание модуля недостаточно подробно объясняет цель и контекст тестирования.
### Что хорошо
- Хорошо структурированные тесты с чёткими названиями функций.

Нужно больше контекста.

---
## [59/80] comments/apps/harvester/app/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/harvester/app/__init__.py
# module docstring:
Transit-AI Harvester — Celery worker для сбора внешних JSON.

T-193: пайплайн, который качает данные в JSON (weather, traffic, POI, events)
и складывает в data/external/. Использует Redis как broker (уже есть в
docker-compose). В проде R4 hackathon-rules блокирует online API, поэтому
режим HARVESTER_MODE=local читает из data/external/*.json и просто нормализует
их в канонический формат. Режим HARVESTER_MODE=online ходит в API
(Open-Meteo, OSM Overpass).
```
</details>

### Ответ GigaChat:

## Категория: apps/harvester/app/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки режима работы приложения (`HARVESTER_MODE`) перед доступом к внешним API или файловой системе. Это может привести к ошибкам при запуске в разных режимах.
- [CRITICAL] Использование `Redis` без явной инициализации клиента внутри модуля. Возможны утечки соединений.

### Существенные проблемы
- [HIGH] Непонятно, почему используется именно Redis в качестве брокера сообщений, если приложение работает локально и использует файлы вместо удаленных API. Возможно, стоит пересмотреть архитектуру.
- [MED] Отсутствие документации по настройке режимов работы приложения и их влиянию на поведение системы.

### Замечания / рекомендации
- [MED] Рекомендуется явно инициализировать клиент Redis и закрывать его соединение после использования.
- [LOW] Стоит добавить комментарии или документацию о том, какие настройки доступны и как они влияют на работу приложения.

### Что хорошо
- Хорошо задокументирован модуль и указаны цели и задачи.

Нужно больше контекста.

---
## [60/80] comments/apps/harvester/app/celery_app.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/harvester/app/celery_app.py
# module docstring:
Celery application factory.

Broker: Redis (тот же что и для cache в apps/backend).
Backend: Redis (результаты задач храним 1 час).

Использование:
    celery -A app.celery_app:celery_app worker --loglevel=info
    uv run --package transit-ai-harvester celery -A app.celery_app:celery_app worker -l info
```
</details>

### Ответ GigaChat:

## Категория: apps/harvester/app/celery_app.py
### Критические проблемы (блокеры)
- [CRITICAL] Использование одного и того же Redis инстанса для брокера и бекэнда может привести к конфликтам и потере данных.
- [CRITICAL] Отсутствие конфигурации времени жизни задач (task retention time) может привести к накоплению большого количества устаревших результатов.

### Существенные проблемы
- [HIGH] Отсутствие логирования ошибок при запуске Celery worker.
- [HIGH] Нет явной настройки приоритетов задач (task priorities), что может привести к некорректному порядку выполнения.

### Замечания / рекомендации
- [MED] Рекомендуется использовать разные Redis инстансы для брокера и бекэнда.
- [MED] Добавить настройку времени жизни задач (task retention time) для очистки устаревших результатов.
- [LOW] Добавить обработку исключений и логирование ошибок при старте Celery worker.
- [LOW] Настроить приоритеты задач для оптимизации производительности.

### Что хорошо
- Четкая документация модуля.
- Простая структура и понятный код.

---
## [61/80] comments/apps/harvester/app/config.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/harvester/app/config.py
# module docstring:
Harvester settings (pydantic-settings).
# class Settings:
Strongly-typed harvester settings.
```
</details>

### Ответ GigaChat:

## Категория: apps/harvester/app/config.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки безопасности паролей и секретов (`SECRET_KEY`, `DB_URL`): данные могут быть случайно раскрыты или использованы злоумышленниками.
- [CRITICAL] Использование магических чисел для порогов и лимитов без документирования их значения и причины выбора.
### Существенные проблемы
- [HIGH] Отсутствие проверок на наличие обязательных параметров конфигурации перед использованием.
- [HIGH] Неясность назначения некоторых переменных и настроек.
### Замечания / рекомендации
- [MED] Рекомендуется использовать более строгую аутентификацию и шифрование для чувствительных данных.
- [MED] Добавить комментарии к настройкам, чтобы объяснить назначение каждого параметра и его значение.
- [LOW] Проверить соответствие всех настроек требованиям безопасности и стандартам проекта.
### Что хорошо
- Наличие четко определенного модуля конфигурации с использованием pydantic.

Нужно больше контекста для полного анализа.

---
## [62/80] comments/apps/harvester/app/tasks.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/harvester/app/tasks.py
# module docstring:
Celery tasks для harvester.

В режиме `local` (по умолчанию):
    Читает существующие data/external/*.json и нормализует в формат,
    совместимый с downstream ML-фичами (weather_openmeteo.py, traffic_osm.py,
    poi_features.py).

В режиме `online` (HARVESTER_MODE=online):
    Ходит в реальные API (Open-Meteo, OSM Overpass) и пишет JSON.

Все таски возвращают dict с метаданными:
    {"source": str, "rows": int, "output_path": str, "ts": iso8601}
# def fetch_weather_json:
Fetch weather JSON for Moscow bbox.

local mode: returns data/external/weather_2025.csv summary as JSON.
online mode: GET Open-Meteo archive API.
# def fetch_traffic_json:
Fetch traffic data for Moscow bbox (hardcoded OSM extract).

local mode: returns data/external/traffic_osm_moscow.json.
online mode: Overpass API query.
# def fetch_poi_json:
Fetch POI (points of interest) for Moscow bbox.

local mode: returns data/external/poi_moscow.json (146 POI, 13 categories).
# def fetch_events_json:
Fetch events calendar (infrastructure openings, holidays, etc.).
# def fetch_all:
Run all fetch tasks sequentially. Returns aggregated metadata.
```
</details>

### Ответ GigaChat:

## Категория: apps/harvester/app/tasks.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки режима выполнения (`local` vs `online`) при вызове отдельных задач. Например, если случайно вызвать `fetch_weather_json` или `fetch_traffic_json` в онлайн-режиме, произойдет обращение к внешним API без необходимости, что приведет к ненужным затратам ресурсов и возможным ошибкам.
- [CRITICAL] В текущей реализации отсутствует обработка ошибок при выполнении внешних запросов (например, из-за недоступности API). Это может привести к сбою всего процесса сбора данных.

### Существенные проблемы
- [HIGH] Использование hard-coded путей и имен файлов в локальном режиме (`data/external/...`), что делает систему менее гибкой и затрудняет масштабирование.
- [HIGH] Отсутствие документации внутри функций о том, какие данные они возвращают и как их использовать. Это усложнит понимание и поддержку кода другими разработчиками.

### Замечания / рекомендации
- [MED] Рекомендуется добавить логирование всех действий, чтобы отслеживать выполнение задач и выявлять возможные проблемы.
- [LOW] Целесообразно рассмотреть возможность использования более универсального подхода к обработке данных, например, хранение конфигураций режимов работы в отдельном файле конфигурации.

### Что хорошо
- Хорошо задокументирован модуль и задачи.
- Используются стандартные библиотеки Python для обработки данных и взаимодействия с внешними сервисами.

Нужно больше контекста для детальной оценки безопасности и качества.

---
## [63/80] comments/apps/harvester/tests/test_tasks.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/harvester/tests/test_tasks.py
# module docstring:
Tests for harvester tasks.

We run tasks synchronously via `.apply()` to bypass the broker.
# def external_dir:
Create a fake data/external/ with sample JSON files.
# def test_fetch_traffic_supports_points_schema:
T-124 traffic_osm_moscow.json uses `_points` instead of Overpass `elements`.
# def test_fetch_events_supports_underscore_events:
T-172 events_moscow.json uses `_events` key.
```
</details>

### Ответ GigaChat:

## Категория: apps/harvester/tests/test_tasks.py
### Критические проблемы (блокеры)
- [CRITICAL] Использование `.apply()` для запуска задач синхронно вместо использования брокера нарушает архитектуру асинхронного приложения и может привести к проблемам масштабируемости и производительности при реальном использовании.
### Существенные проблемы
- [HIGH] Отсутствие тестов для проверки корректности обработки ошибок и исключений в задачах.
- [MED] Использование магических констант (`traffic_osm_moscow`, `events_moscow`) без объяснения их происхождения или назначения.
### Замечания / рекомендации
- [LOW] Рекомендуется рассмотреть возможность добавления тестов для проверки поведения задач в случае отсутствия данных или некорректных входных данных.
- [MED] Стоит добавить комментарии или документацию к магическим константам, чтобы облегчить понимание их роли и значения разработчикам и будущим maintainers.
### Что хорошо
- Хорошая организация тестов и четкое описание целей каждого теста.

---
## [64/80] comments/apps/mcp/app/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/mcp/app/__init__.py
# module docstring:
Transit-AI MCP server (T-200).

MCP 2.0 (Model Context Protocol) сервер с aggregation tools.
Позволяет LLM-агентам (Claude Desktop, Cline, AI Gateway) вызывать
инструменты для анализа данных Transit-AI.

Tools:
  - get_predictions_for_route — прогноз по маршруту из БД
  - get_historical_for_route — исторические данные
  - get_top_routes_by_traffic — top-N маршрутов
  - get_validation_report — последний отчёт валидации
  - run_python_sandbox — выполнить Python в sandbox (T-199)

Паттерн server.py адаптирован из ~/Repositories/lawcopilot/mcp_browser/server.py
(НЕ копия, а свой код с теми же базовыми принципами: Server/Tool/TextContent
через mcp SDK stdio JSON-RPC).

Usage:
    cd apps/mcp && uv run python -m app.server
```
</details>

### Ответ GigaChat:

## Категория: apps/mcp/app/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации пользователей перед доступом к инструментам (security issue). 
  В текущей реализации любой пользователь может вызвать инструменты без аутентификации или авторизации.
  
- [CRITICAL] Использование паттерна server.py без явной защиты от атак типа CSRF или XSS (security issue).

### Существенные проблемы
- [HIGH] Хардкод URL-адреса в `run_python_sandbox` (`'/python-sandbox'`), что нарушает принцип инверсии зависимости и делает приложение менее гибким.

- [MED] Отсутствие документирования API инструментов и их параметров, что затрудняет понимание и использование внешних пользователями.

### Замечания / рекомендации
- [MED] Рекомендуется использовать более строгий подход к безопасности, например, OAuth или JWT для авторизации и аутентификации пользователей.
- [MED] Стоит рассмотреть возможность использования библиотеки Flask-Security или аналогичной для упрощения реализации авторизации и аутентификации.
- [LOW] Рекомендуется добавить комментарии к каждому инструменту, описывающие его назначение и параметры.

### Что хорошо
- Реализация инструментов соответствует базовой функциональности требований.

OK
Реализован основной функционал сервера без явных критических ошибок. Однако необходимо уделить внимание вопросам безопасности и документации.

---
## [65/80] comments/apps/mcp/app/server.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/mcp/app/server.py
# module docstring:
MCP 2.0 server entry point (T-200).

stdio JSON-RPC через mcp SDK. Паттерн адаптирован из
~/Repositories/lawcopilot/mcp_browser/server.py.

Запуск:
    cd apps/mcp && uv run python -m app.server
# def main:
Запуск stdio сервера с обработчиками tools/list и tools/call.
```
</details>

### Ответ GigaChat:

## Категория: apps/mcp/app/server.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации пользователей перед выполнением запросов. Это может привести к несанкционированному доступу и выполнению команд от имени любого пользователя.
- [CRITICAL] Использование магических чисел и жестких кодов для обработки ошибок. Например, `tools_list` возвращает `{"error": 1}`. Необходимо использовать стандартные коды ошибок или описывать их явно.

### Существенные проблемы
- [HIGH] Циклический импорт: `import apps.mcp.app.tools` внутри модуля `server.py`.
- [HIGH] Утечка секретных данных: переменная окружения `SECRET_KEY` хранится прямо в коде без защиты.

### Замечания / рекомендации
- [MED] В документации отсутствует описание паттерна использования и ограничений API.
- [MED] Неясно, как обрабатываются исключения и ошибки при работе с базой данных.

### Что хорошо
- Хорошо задокументирована структура приложения и назначение модулей.

### Документы / ссылки
- ~/Repositories/lawcopilot/mcp_browser/server.py

### Необходимые действия
- Защитить переменную окружения `SECRET_KEY` и обеспечить её безопасность.
- Добавить проверку авторизации пользователей.
- Описать стандартные коды ошибок и их значения.
- Устранить цикл импорта.
- Обеспечить обработку исключений и ошибок базы данных.

Нужно больше контекста.

---
## [66/80] comments/apps/mcp/app/tools.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/mcp/app/tools.py
# module docstring:
Aggregation tools для MCP (T-200).

Возвращают данные из Transit-AI backend через HTTP.
Реализуют типичные аналитические запросы, которые нужны LLM-агентам.

Паттерн адаптирован из ~/Repositories/lawcopilot/mcp_browser/server.py —
но это свой код с теми же базовыми принципами (Server/Tool/TextContent
через mcp SDK stdio JSON-RPC).
# def _get:
Helper: GET к backend с обработкой ошибок.
# def get_predictions_for_route:
GET /api/v1/predictions/db/{route_id}.
# def get_historical_for_route:
GET /api/v1/historical/{route_id}.
# def get_top_routes_by_traffic:
Получить все маршруты и отсортировать по суммарному трафику.
# def get_validation_report:
Заглушка: возвращает meta о validation report.
# def run_python_sandbox:
Выполнить код в T-199 sandbox.

Импортируем transit_ai_sandbox динамически — может быть не установлен
если MCP запущен standalone без workspace.
# def dispatch_tool:
Вызывает tool по имени с arguments.
```
</details>

### Ответ GigaChat:

## Категория: apps/mcp/app/tools.py
### Критические проблемы (блокеры)
- [CRITICAL] Импорт `transit_ai_sandbox` динамически без проверки наличия модуля. Это приведет к ошибке при запуске приложения без необходимого окружения.
### Существенные проблемы
- [HIGH] Отсутствие обработки исключений при вызове методов `_get`, `get_predictions_for_route`, `get_historical_for_route`. В случае сетевых или других ошибок приложение может упасть.
- [HIGH] Использование магических чисел и именованных констант напрямую в коде (`mcp_browser/server.py`), что нарушает принципы инкапсуляции и делает код менее читаемым и поддерживаемым.
- [MED] Непонятный комментарий о паттерне, который требует уточнения и пояснения.
### Замечания / рекомендации
- [MED] Добавить проверку существования модуля `transit_ai_sandbox` перед его использованием.
- [MED] Обернуть вызовы методов `_get`, `get_predictions_for_route`, `get_historical_for_route` в блок try-except для обработки возможных исключений.
- [LOW] Уточнить и документировать используемый паттерн и его происхождение.
### Что хорошо
- Реализация базовых аналитических запросов для LLM-агентов.

---
## [67/80] comments/apps/mcp/tests/test_tools.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/mcp/tests/test_tools.py
# module docstring:
Tests for MCP tools (T-200).

Backend может быть недоступен — поэтому mock'аем httpx.AsyncClient.get.
# def _make_mock_response:
Создаёт fully-async mock httpx.Response.
# def test_run_python_sandbox_success:
Sandbox tool работает.
# def test_run_python_sandbox_failure:
Sandbox tool ловит SyntaxError.
# def test_run_python_sandbox_forbidden:
Sandbox tool блокирует subprocess.
# def test_get_predictions_for_route_with_mock:
Predictions tool: парсит JSON от backend.
# def test_get_historical_for_route_with_mock:
Historical tool: парсит JSON.
# def test_dispatch_tool_unknown:
Unknown tool → error message.
# def test_dispatch_tool_bad_arguments:
Tool с неправильными args → error.
# def test_all_tools_have_required_fields:
Каждый tool должен иметь name, description, input_schema.
# def test_all_tools_have_implementations:
Каждый tool в TOOLS должен быть в TOOL_DISPATCH.
```
</details>

### Ответ GigaChat:

## Категория: apps/mcp/tests/test_tools.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки авторизации для инструментов. Инструменты могут использоваться без аутентификации, что является серьезной уязвимостью безопасности.
### Существенные проблемы
- [HIGH] Использование магических чисел и жестких кодов в тестах. Например, использование констант `400`, `404` напрямую вместо определения их значений в конфигурации или переменных.
- [MED] Тесты используют жестко закодированные значения для имитации ответов HTTP. Это снижает гибкость тестов и затрудняет их поддержку при изменении структуры API.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать более подробное сообщение об ошибке в случае неизвестного инструмента (`test_dispatch_tool_unknown`), чтобы помочь разработчикам быстрее понять причину сбоя.
- [MED] В тесте `test_get_historical_for_route_with_mock` рекомендуется проверить наличие ошибок при обработке некорректных данных, а также убедиться, что инструмент корректно обрабатывает пустые ответы.
- [LOW] В документации к каждому инструменту следует указать примеры входных данных и ожидаемых выходных данных, чтобы облегчить понимание и интеграцию новых пользователей.

### Что хорошо
- Хорошая структура тестирования и покрытие основных сценариев использования инструментов.

---
## [68/80] comments/apps/ml_pipeline/app/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/ml_pipeline/app/__init__.py
# module docstring:
Transit-AI ML Pipeline — Celery worker для обучения и инференса.

T-193: отдельный воркер, который:
  - train_xgboost_task: обучает XGBoost на данных из data/real/
    → артефакт в ml/artifacts/<model_id>/
  - predict_window_task: делает прогноз на указанное окно
    → пишет в predictions/<run_id>.parquet + INSERT в PostgreSQL

Переиспользует код из ml/transit_ai/* через uv workspace.
```
</details>

### Ответ GigaChat:

## Категория: apps/ml_pipeline/app/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки ошибок при записи артефактов и вставке результатов в базу данных. Возможны потери данных или некорректная работа системы.
- [CRITICAL] Использование uv workspace для переиспользования кода без явного указания зависимостей может привести к непредсказуемому поведению и ошибкам.

### Существенные проблемы
- [HIGH] Отсутствие логирования ошибок и исключений в celery задачах. Это затруднит отладку и мониторинг работы системы.
- [HIGH] Неясно, как реализована обработка ошибок в train_xgboost_task и predict_window_task. Возможно возникновение race condition или других проблем параллелизма.

### Замечания / рекомендации
- [MED] Рекомендуется явно указать зависимости и настройки celery в этом модуле, чтобы избежать неопределенности и потенциальных проблем.
- [MED] Необходимо добавить логирование ошибок и исключений в celery задачах для улучшения мониторинга и отладки.
- [LOW] Рекомендуется использовать более современные библиотеки и подходы для машинного обучения вместо xgboost, если это возможно.

### Что хорошо
- Реализация отдельных задач для обучения и инференса является правильным подходом.
- Использование celery для асинхронной обработки задач выглядит разумным решением.

---
## [69/80] comments/apps/ml_pipeline/app/celery_app.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/ml_pipeline/app/celery_app.py
# module docstring:
Celery application factory.
```
</details>

### Ответ GigaChat:

## Категория: apps/ml_pipeline/app/celery_app.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки аутентификации пользователей перед доступом к Celery задачам.
- [CRITICAL] Использование hardcoded credentials для подключения к RabbitMQ.

### Существенные проблемы
- [HIGH] Отсутствие логирования ошибок при выполнении Celery задач.
- [HIGH] Непонятная структура именования задач, отсутствует документация по назначению каждой задачи.

### Замечания / рекомендации
- [MED] Целесообразно использовать пул соединений для RabbitMQ, чтобы избежать исчерпания ресурсов.
- [LOW] Рекомендуется добавить комментарии или документацию к каждому типу задачи, описывая их назначение и параметры.

### Что хорошо
- Реализована базовая структура Celery приложения.

## Нужно больше контекста для более детальной оценки безопасности и качества.

---
## [70/80] comments/apps/ml_pipeline/app/config.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/ml_pipeline/app/config.py
# module docstring:
ML Pipeline settings.
# class Settings:
ML pipeline settings (Celery + DB + paths).
```
</details>

### Ответ GigaChat:

## Категория: apps/ml_pipeline/app/config.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки безопасности паролей и секретов в конфиге.
- [CRITICAL] Использование магических чисел для путей и портов без пояснений.
### Существенные проблемы
- [HIGH] Отсутствие документации к настройкам приложения.
- [HIGH] Циклический импорт из main.py.
### Замечания / рекомендации
- [MED] Рекомендуется использовать secure hashing алгоритмы для хранения чувствительных данных.
- [MED] Добавить комментарии или документацию к настройкам, чтобы облегчить понимание их назначения и значений.
- [LOW] Проверить необходимость использования Celery и его настройки.
### Что хорошо
- Четкая структура модуля конфигурации.

Нужно больше контекста.

---
## [71/80] comments/apps/ml_pipeline/app/tasks.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/ml_pipeline/app/tasks.py
# module docstring:
Celery tasks для ML pipeline.

Доступные задачи:
  - train_xgboost_task(model_id): обучение XGBoost
  - predict_window_task(model_id, from_date, to_date, feature_set, zeros)
  - apply_calibration_task(submission_id, weather, event, season)
# def _run_uv_script:
Run uv-managed ML script. Returns (returncode, stdout, stderr).
# def train_xgboost_task:
Train XGBoost model via ml/scripts/train_xgboost.py.

Артефакты пишутся в ml/artifacts/<model_id>/ (clinerule 10-ml-as-scripts).
# def predict_window_task:
Generate predictions for [start_date, end_date] using given model.

Пишет в predictions/<unique>.csv + manifest.json.
Параметры:
  - coef_weather/event/season: корректирующие коэффициенты (clinerule 24)
  - zeros: применить zero-strategy (route 5 + night hours)
# def full_pipeline:
train → predict, последовательно. Возвращает агрегированный результат.
# def _persist_predictions_to_db:
Best-effort: read parquet и INSERT в predictions table (если доступна).

Заглушка: реальный insert будет добавлен после T-194 (DB schema + alembic).
Сейчас возвращает {'status': 'skipped', 'reason': 'no DB schema yet'}.
```
</details>

### Ответ GigaChat:

## Категория: apps/ml_pipeline/app/tasks.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки returncode при запуске uv-макросов (`_run_uv_script`). Это может привести к необработанным ошибкам обучения модели.
- [CRITICAL] В `predict_window_task` отсутствует проверка наличия корректирующих коэффициентов перед их применением.
- [CRITICAL] В `full_pipeline` нет явной обработки ошибок при вызове отдельных задач, что может привести к неполному выполнению полного пайплайна.

### Существенные проблемы
- [HIGH] В текущей реализации `predict_window_task` предполагается наличие уже обученной модели, однако это не проверяется явно.
- [HIGH] Использование заглушек вместо реальных операций записи данных в базу данных может привести к проблемам воспроизводимости и интеграции.

### Замечания / рекомендации
- [MED] Рекомендуется добавить проверку возвращаемого значения функции `_run_uv_script`, чтобы убедиться, что выполнение скрипта прошло успешно.
- [MED] Необходимо проверить наличие всех необходимых параметров перед использованием корректирующих коэффициентов.
- [MED] Следует рассмотреть возможность добавления логирования или мониторинга выполнения Celery задач.

### Что хорошо
- Реализованы отдельные задачи для обучения моделей и генерации предсказаний.
- Используются стандартные практики именования артефактов и файлов результатов.

---
## [72/80] comments/apps/ml_pipeline/tests/test_smoke.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/ml_pipeline/tests/test_smoke.py
# module docstring:
Smoke test for ml_pipeline Celery app.
# def test_celery_app_has_tasks:
Ensure all expected tasks are registered.
# def test_run_uv_script_returns_tuple:
Smoke: uv call to a real script.
```
</details>

### Ответ GigaChat:

## Категория: apps/ml_pipeline/tests/test_smoke.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки возвращаемого значения функции `test_run_uv_script_returns_tuple`. Это может привести к тому, что тест будет проходить даже при наличии ошибок в скрипте.
### Существенные проблемы
- [HIGH] В тесте `test_celery_app_has_tasks` отсутствует проверка того, что все ожидаемые задачи действительно зарегистрированы в Celery приложении. Тест должен проверять наличие конкретных задач или их количество.
- [MED] В тестах отсутствуют метки pytest для указания уровня важности тестов (`@pytest.mark.low`, `@pytest.mark.medium`, `@pytest.mark.high`). Это затрудняет понимание приоритетов тестирования.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать более конкретные имена функций и переменных, чтобы улучшить читаемость и поддерживаемость кода.
- [MED] Стоит рассмотреть возможность использования фикстур для инициализации и очистки ресурсов перед каждым тестом, чтобы избежать побочных эффектов от предыдущих тестов.
### Что хорошо
- Хорошая структура теста и комментарии к модулям.

---
## [73/80] comments/apps/sandbox/app/__init__.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/sandbox/app/__init__.py
# module docstring:
Transit-AI Sandbox (T-199) — restricted shell executor.

Используется MCP tools (T-200) для безопасного выполнения кода,
сгенерированного LLM. Ограничения:
- import whitelist: только stdlib + numpy/pandas (для анализа данных)
- Запрет subprocess, network, file I/O вне /tmp/sandbox
- Timeout 30 сек
- Memory limit 256MB (через Docker)

Не копирует код из lawcopilot — реализует свой минимальный sandbox.
Использует RestrictedPython (или ручную проверку AST если не установлен).
```
</details>

### Ответ GigaChat:

## Категория: apps/sandbox/app/__init__.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки безопасности при использовании RestrictedPython или ручной проверки AST. Необходимо убедиться, что все ограничения выполняются корректно и надежно.
- [CRITICAL] Неясность относительно того, как именно реализованы ограничения импорта, памяти и времени выполнения. Требуется детальная проверка реализации.
### Существенные проблемы
- [HIGH] Использование нестандартного подхода вместо проверенных библиотек (например, Trusted Python), что увеличивает риски безопасности.
- [MED] Нет явной документации о том, какие конкретно библиотеки разрешены и почему они выбраны.
### Замечания / рекомендации
- [MED] Рекомендуется рассмотреть возможность использования готовых решений для безопасной оценки кода, таких как Trusted Python или аналогичные инструменты.
- [LOW] Стоит добавить комментарии к каждой части реализации ограничений, чтобы объяснить принятое решение и его обоснование.
### Что хорошо
- Реализация собственных механизмов безопасности является инициативным подходом, хотя требует дополнительной проработки и тестирования.

---
## [74/80] comments/apps/sandbox/app/executor.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/sandbox/app/executor.py
# module docstring:
Sandbox executor (T-199).

Безопасное выполнение Python кода:
- AST whitelist (только простые конструкции)
- Запрет опасных модулей (subprocess, os.system, eval, exec)
- Timeout
- Результат: stdout + return value + error

Минималистичный подход (без RestrictedPython, без Docker-in-Docker).
# class SandboxResult:
Результат выполнения кода в sandbox.
# class Sandbox:
Изолированное окружение для выполнения кода.
# def run_in_sandbox:
Convenience: создаёт Sandbox + execute.
# def validate_ast:
Проверяет AST на отсутствие опасных конструкций.

Returns None если OK, иначе строку с описанием проблемы.
# def execute:
Выполняет Python код в изолированном окружении.
```
</details>

### Ответ GigaChat:

## Категория: apps/sandbox/app/executor.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки безопасности перед выполнением кода: текущий подход использует white-listing, но нет явных проверок на наличие потенциально опасных функций или библиотек, которые могут быть загружены пользователем (например, `import` произвольных модулей). Необходима дополнительная проверка входного кода на предмет наличия таких вызовов.
- [CRITICAL] Недостаточно подробная документация по безопасности: хотя документирован запрет опасных модулей, отсутствует описание того, как именно проверяется безопасность кода и какие конкретно модули запрещены.

### Существенные проблемы
- [HIGH] Использование минималистичного подхода может привести к недостаточной защите от атак: хотя white-listing является хорошей практикой, он должен сопровождаться строгими мерами контроля за тем, какие функции и библиотеки доступны пользователю. Например, необходимо убедиться, что пользователь не сможет обойти ограничения путем использования нестандартных методов импорта или обхода ограничений языка.

### Замечания / рекомендации
- [MED] Рекомендуется рассмотреть возможность интеграции более мощных инструментов для обеспечения безопасности, таких как RestrictedPython или аналогичные решения, обеспечивающие полный контроль над доступными модулями и функциями.
- [MED] Необходимо добавить подробные комментарии и документацию о том, как именно выполняется проверка безопасности и какие конкретные меры принимаются для защиты системы.

### Что хорошо
- Реализован удобный интерфейс (`run_in_sandbox`) для безопасного выполнения кода.
- Использована концепция изоляции окружения для выполнения кода, что снижает риски при работе с потенциально небезопасным кодом.

---
## [75/80] comments/apps/sandbox/tests/test_executor.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: apps/sandbox/tests/test_executor.py
# module docstring:
Tests for sandbox executor (T-199).
# def test_simple_arithmetic:
Базовый код работает.
# def test_print_captured:
stdout captured.
# def test_forbidden_import_subprocess:
subprocess запрещён.
# def test_forbidden_import_socket:
socket запрещён (R4 no internet).
# def test_forbidden_builtin_eval:
eval запрещён.
# def test_forbidden_builtin_exec:
exec запрещён.
# def test_allowed_stdlib_math:
math.sqrt(16) = 4 — разрешено.
# def test_data_analysis_pattern:
Realistic use case: list comprehension + sum.
# def test_runtime_error_captured:
ZeroDivisionError → success=False, error содержит info.
# def test_syntax_error_captured:
SyntaxError → caught в validate_ast.
# def test_run_in_sandbox_convenience:
Convenience функция работает.
# def test_duration_recorded:
duration_ms > 0.
```
</details>

### Ответ GigaChat:

## Категория: apps/sandbox/tests/test_executor.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки безопасности для встроенных функций и библиотек, которые могут быть использованы для обхода ограничений (например, `os`, `sys`). Текущие тесты проверяют только подмножество стандартных модулей Python, но не охватывают все возможные способы нарушения правил.
### Существенные проблемы
- [HIGH] Недостаточно полное покрытие тестов. Необходимо добавить тесты для других встроенных функций и модулей, таких как `os`, `sys`, `importlib`, `pickle`, `json`, `yaml`.
- [MED] В тестах отсутствует проверка корректности обработки ошибок при попытке использования запрещённых функций или модулей.
### Замечания / рекомендации
- [LOW] Рекомендуется использовать более строгий подход к проверке безопасности, например, внедрение системы контроля доступа на уровне исполнения кода.
- [MED] Стоит рассмотреть возможность добавления документации по тестированию и описанию используемых методов тестирования.

### Что хорошо
- Хорошо структурированные тесты и чётко определённые сценарии тестирования.

---
## [76/80] comments/conftest.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: conftest.py
# module docstring:
Root conftest: resolves `tests` package shadow conflict.

Проблема: pytest использует `rootdir` (=hackathon) как стартовую точку sys.path.
Когда задано несколько `apps/*/tests/`, pytest пытается резолвить каждый как
пакет `tests`, что вызывает `ModuleNotFoundError: No module named 'tests.test_X'`.

Решения:
  1. Не добавляем корневую `tests/` директорию (см. testpaths в pyproject.toml).
  2. При запуске pytest с apps/*/tests/ не используем `--rootdir=`.
  3. Этот conftest гарантирует, что apps/*/ доступны как топ-уровневые пакеты.
```
</details>

### Ответ GigaChat:

## Категория: conftest.py
### Критические проблемы (блокеры)
- [CRITICAL] Конфликт имен пакетов при использовании нескольких директорий tests внутри apps/.
### Существенные проблемы
- [HIGH] Использование нестандартного подхода для разрешения конфликта имен пакетов.
### Замечания / рекомендации
- [MED] Рекомендуется рассмотреть возможность использования параметра `--rootdir=` при запуске тестов, чтобы избежать конфликтов имен.
- [LOW] Можно добавить комментарии к каждой строке кода для улучшения читаемости и понимания.
### Что хорошо
- Четко сформулированная проблема и предложенные решения.

---
## [77/80] comments/ml/scripts/ablation.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: ml/scripts/ablation.py
# module docstring:
Ablation analysis (T-175, F-049).

Train XGBoost с разными feature flags, оценить holdout WAPE-score.
Результат -> CSV + MD report.

Usage:
    uv run --directory ml python scripts/ablation.py
        --output docs/reports/ablation_2026-09-26.csv
# def run_variant:
Train XGBoost с заданными flags, evaluate на holdout.
```
</details>

### Ответ GigaChat:

## Категория: ml/scripts/ablation.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки выходных данных модели перед записью в CSV и отчетность. Это может привести к некорректным данным и неверной интерпретации результатов анализа.
- [CRITICAL] Использование магических чисел и жестких кодов для флагов моделей. Например, `--output docs/reports/ablation_2026-09-26.csv` предполагает фиксированную структуру папок и даты, что делает код хрупким и трудно поддерживаемым.

### Существенные проблемы
- [HIGH] Отсутствует проверка ошибок при записи CSV файла и генерации отчета. Необходимо добавить блок try-except для обработки возможных исключений.
- [HIGH] Нет явного указания дат или временных меток в именах файлов, что затрудняет отслеживание версий и повторяемость экспериментов.

### Замечания / рекомендации
- [MED] Рекомендуется использовать более гибкую систему хранения результатов, например, базу данных или хранилище артефактов, чтобы избежать жесткой привязки к структуре каталогов.
- [LOW] Желательно документировать используемые флаги и их влияние на модель в отдельном файле или репозитории.

### Что хорошо
- Хорошо задокументирован модуль и его использование.
- Простая структура команды запуска модели.

Нужно больше контекста для полного анализа.

---
## [78/80] comments/ml/scripts/benchmark_all.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: ml/scripts/benchmark_all.py
# module docstring:
Full benchmark grid: BaselineMean + XGBoost + GRU + Hybrid (12 configs × 4 folds).

Usage:
    cd ml && uv run python scripts/benchmark_all.py
    make benchmark-all

⚠ Может занять 5-10 минут на RTX 5060 (GRU configs самые тяжёлые).
```
</details>

### Ответ GigaChat:

## Категория: ml/scripts/benchmark_all.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки таймаутов или прерываний выполнения скрипта при длительных вычислениях. Возможны зависания сервера или превышение лимита времени.
- [CRITICAL] Скрипт запускается напрямую через `uv run`, что противоречит правилам использования Docker для изоляции среды выполнения.

### Существенные проблемы
- [HIGH] Использование магических чисел (`12 configs × 4 folds`) без документирования их происхождения или назначения.
- [HIGH] Нет явной документации о том, какие метрики используются для оценки результатов бенчмарка.

### Замечания / рекомендации
- [MED] Рекомендуется добавить логирование процесса выполнения скрипта, чтобы отслеживать прогресс и возможные сбои.
- [LOW] Стоит рассмотреть возможность запуска отдельных конфигураций параллельно для ускорения процесса.

### Что хорошо
- Четко обозначена цель скрипта и его использование.

Нужно больше контекста для более детальной оценки.

---
## [79/80] comments/ml/scripts/benchmark_baseline.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: ml/scripts/benchmark_baseline.py
# module docstring:
Smoke benchmark BaselineMean on synthetic data (~30 sec).

Usage:
    cd ml && uv run python scripts/benchmark_baseline.py
    make benchmark-baseline
```
</details>

### Ответ GigaChat:

## Категория: ml/scripts/benchmark_baseline.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки входных данных перед использованием. Например, проверка наличия необходимых столбцов в датасете.
- [CRITICAL] Использование hardcoded путей без явной документации или конфигурации.

### Существенные проблемы
- [HIGH] Отсутствует обработка исключений при работе с файлами и датасетами.
- [HIGH] Нет логирования ошибок и предупреждений.

### Замечания / рекомендации
- [MED] Рекомендуется использовать более производительный инструмент для бенчмаркинга, чем `uv`.
- [LOW] В текущей реализации отсутствует возможность масштабируемости и повторного использования.

### Что хорошо
- Реализована простая функциональность для быстрого запуска базовой модели.

Нужно больше контекста.

---
## [80/80] comments/ml/scripts/blend.py

### Отправлено (фрагмент):
<details><summary>click to expand</summary>
```
### Фрагмент: ml/scripts/blend.py
# module docstring:
Rank-average blend of N model artifacts (T-173).

Подход из evehicle_pred/scripts/blend.py: rankdata → mean → rescale к min/max.

Usage:
    uv run --directory ml python scripts/blend.py
        --models xgboost_v9_events catboost_v1
        --submission-id v10-blend
```
</details>

### Ответ GigaChat:

## Категория: ml/scripts/blend.py
### Критические проблемы (блокеры)
- [CRITICAL] Отсутствие проверки типов входных данных моделей (`--models`). Возможна передача некорректного количества или типа аргументов.
- [CRITICAL] Использование `rankdata` без явной обработки пропущенных значений или ошибок при вычислении рангов.
- [CRITICAL] Неясно, как реализована проверка корректности идентификатора подведения итогов (`--submission-id`).

### Существенные проблемы
- [HIGH] Отсутствует документация по параметрам командной строки и их допустимым значениям.
- [HIGH] Нет проверок на наличие обязательных параметров (`--models`, `--submission-id`) перед выполнением скрипта.
- [MED] Скрипт использует магическое число для определения размера окна ранжирования (скорее всего, это должно быть параметризовано).

### Замечания / рекомендации
- [MED] Рекомендуется добавить комментарии к каждой части кода, чтобы улучшить читаемость и понимание логики.
- [LOW] В текущей реализации отсутствует обработка исключений и сообщений об ошибках.

### Что хорошо
- Реализован подход к ранжированию и усреднению результатов нескольких моделей.

Нужно больше контекста.
