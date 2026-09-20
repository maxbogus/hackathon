# 16-tdd-cycle.md — RED → GREEN → REFACTOR

## Обязательный цикл для каждого тикета

Каждый тикет реализуется через TDD. Никаких "сначала напишу код, потом тест".

## Фазы

### RED: написать падающий тест

1. Выбрать тикет из `make backlog-ready`
2. Пометить `status: in-progress` в YAML frontmatter
3. Написать **минимальный падающий тест**, который проверяет acceptance criterion

```python
# tests/test_predictions.py
def test_get_predictions_for_stop_returns_value():
    # Arrange
    client = TestClient(app)
    # Act
    response = client.get("/api/v1/predictions/stop/42")
    # Assert
    assert response.status_code == 200
    assert "value" in response.json()
```

4. Запустить тест: `uv run pytest tests/test_predictions.py::test_get_predictions_for_stop_returns_value -v`
5. Убедиться что он **падает** с понятной ошибкой

### GREEN: минимальный код

1. Написать **минимальный** код, чтобы тест прошёл
2. **Не** оптимизировать, **не** рефакторить, **не** добавлять "на будущее"
3. Следовать принципу YAGNI

```python
# apps/backend/app/api/predictions.py
@router.get("/predictions/stop/{stop_id}")
def get_predictions(stop_id: int) -> dict:
    return {"value": 0.0, "lower": 0.0, "upper": 0.0}
```

4. Запустить тест ещё раз: `uv run pytest ... -v`
5. Убедиться что он **проходит**

### REFACTOR: улучшить код

1. Теперь — оптимизация, типизация, документация
2. Убрать дублирование (DRY)
3. Добавить типизацию (mypy strict)
4. Добавить docstrings
5. **НЕ** менять поведение (тесты должны проходить до и после)

```python
@router.get("/predictions/stop/{stop_id}", response_model=PredictionResponse)
async def get_predictions(
    stop_id: int,
    loader: ArtifactLoader = Depends(get_loader),
) -> PredictionResponse:
    """Get passenger flow prediction for a stop.

    Reads active model artifact from ml/artifacts/active/.
    Returns mean prediction with confidence interval.
    """
    artifact = loader.get_active()
    return artifact.predict(stop_id=stop_id, ...)
```

6. Запустить **все** тесты: `make test`
7. Запустить `make lint` + `make typecheck`

## Definition of Done для тикета

- [ ] Тесты написаны ДО кода (RED → GREEN → REFACTOR)
- [ ] `make check-all` зелёный (lint + typecheck + test)
- [ ] Если менялся OpenAPI — `make api-gen` + `make fe-gen`
- [ ] Если решение RICE > 5 — запись в ledger через `make ledger-add`
- [ ] Conventional Commit с ссылкой на T-NNN
- [ ] YAML frontmatter `status: done`, галочки в Acceptance Criteria
- [ ] Файл перемещён в `docs/backlog/archive/`
- [ ] HANDOFF.md обновлён (`make handoff-update`)

## Типичные ошибки

### ❌ "Сначала код, потом тест"
Без теста нельзя проверить что код работает. Всегда начинай с теста.

### ❌ "Тест слишком большой"
Один тест = одна проверка. Если нужно проверить 5 вещей — 5 тестов.

### ❌ "Я не пишу тесты для тривиального кода"
Любой публичный API = тест. Приватные функции можно не тестировать.

### ❌ "Тест проходит сразу, без RED фазы"
Значит ты написал код до теста. Перепиши: сначала удали код, потом тест, потом код заново.

### ❌ "Я не буду писать тест для config.py"
ОК, но обоснуй в тикете почему. Config часто меняется — тесты окупаются.

## Тестовые маркеры

```python
import pytest

@pytest.mark.unit       # быстрый, без внешних зависимостей
def test_something(): ...

@pytest.mark.integration  # требует Docker (postgres, redis)
def test_with_db(): ...

@pytest.mark.slow         # >5 секунд
def test_full_train(): ...

@pytest.mark.gpu          # требует CUDA
def test_gru_training(): ...
```

Запуск: `uv run pytest -m unit` (только unit), `uv run pytest -m "not gpu"` (без GPU).

## Coverage

```bash
# Цель: >70% для критических модулей, >80% для API
uv run pytest --cov=apps/backend/app --cov-report=term-missing
```

На хакатоне не гонимся за 100% — но критические пути (auth, API endpoints, ML pipeline) должны быть покрыты.

## Когда НЕ TDD

- ❌ Конфиги (yaml, json) — нет смысла тестировать
- ❌ Прототипы для проверки гипотез (но переписать в TDD после подтверждения)
- ❌ Документация
- ❌ Одноразовые скрипты (но `ml/scripts/*.py` лучше тестировать — они будут переиспользоваться)

## TDD + MCP

Когда MCP tool покрывается тестом, тестируется вся цепочка:
- Mock HTTP-ответ от backend
- Проверить JSON Schema валидность input/output
- Проверить что tool регистрируется в `TOOLS` registry
