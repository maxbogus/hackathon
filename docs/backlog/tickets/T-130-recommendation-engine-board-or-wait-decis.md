---
id: T-130
phase: 0
title: бизнес-логика рекомендации «ехать сейчас или подождать» в Streamlit
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.9
  score: 13.5
depends_on: [T-129, T-127]
blocks: []
tags: [frontend, streamlit, passenger, business-logic, beneficiary]
status: backlog
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-130: бизнес-логика рекомендации «ехать сейчас или подождать» в Streamlit

## Context

Боль пассажира: «Ехать сейчас или подождать следующий?» Недостаточно показать данные
(ETA + загрузка) — нужно дать action-oriented рекомендацию. Это превращает UI из «информации»
в «инструмент принятия решения», что и хочет Департамент транспорта.

## Acceptance Criteria

- [ ] Функция `recommend(trams: list[ETAPrediction]) -> str` реализована в `apps/streamlit_app/business.py`
- [ ] Логика: если ближайший рейс загружен <70% → рекомендует «Садитесь»
- [ ] Логика: если загружен 70-90% И следующий приходит <10 мин → рекомендует «Подождите X мин — будет свободнее»
- [ ] Логика: если загружен >90% → рекомендует «Обязательно подождите» (с эмодзи ⚠️)
- [ ] Логика: если ближайший уже ушёл (ETA = 0) → рекомендует следующий
- [ ] Метрика под рекомендацией: «Экономия ~N мин времени ожидания в комфорте»
- [ ] Покрытие unit-тестами: `apps/streamlit_app/tests/test_business.py` (5+ кейсов)
- [ ] UI в режиме «Пассажир» (T-129) вызывает `recommend()` и показывает результат в st.success/st.warning

## Technical Notes

Простая decision tree — никаких ML, чистая бизнес-логика. Это показывает жюри, что мы
понимаем не только данные, но и user experience.

```python
def recommend(trams: list[ETAPrediction]) -> tuple[str, str]:
    """Returns (recommendation_text, emoji)."""
    if not trams:
        return "Нет данных о ближайших рейсах", "❓"
    current = trams[0]
    next_tram = trams[1] if len(trams) > 1 else None
    
    if current.load_pct < 70:
        return "✅ Садитесь — будет комфортно", "✅"
    
    if current.load_pct >= 90:
        if next_tram and next_tram.eta_min <= 10:
            saved_min = next_tram.eta_min
            return f"⚠️ Подождите {saved_min} мин — будет значительно свободнее", "⚠️"
        return "⚠️ Будет тесно — но вариантов нет", "⚠️"
    
    # 70-90%
    if next_tram and next_tram.eta_min <= 8 and next_tram.load_pct < current.load_pct - 15:
        return f"⏳ Подождите {next_tram.eta_min} мин — будет свободнее", "⏳"
    return "✅ Садитесь — загрузка приемлемая", "✅"
```

## Verification

```bash
uv run pytest apps/streamlit_app/tests/test_business.py -v
# Должно быть >= 5 тестов, все зелёные

streamlit run apps/streamlit_app/app.py
# В режиме Пассажир, остановка 1: должна появиться рекомендация
```

## Beneficiary Impact

**Пассажиры (⭐⭐⭐⭐⭐)** — превращает информацию в действие. Action-oriented UX.
**Департамент транспорта** — демонстрирует продуктовое мышление, а не «ML ради ML».

RICE: 13.5 — **топ-3 приоритет** вместе с T-129.
