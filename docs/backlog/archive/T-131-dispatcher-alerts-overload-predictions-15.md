---
id: T-131
phase: 1
title: алерты диспетчеру при прогнозе перегрузки (T-30 мин warning)
priority: P1
effort: 2
unit: hours
rice:
  R: 6
  I: 3.0
  C: 0.9
  score: 8.1
depends_on: []
blocks: []
tags: [backend, frontend, alerts, dispatcher, beneficiary]
status: done
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-131: алерты диспетчеру при прогнозе перегрузки (T-30 мин warning)

## Context

Боль диспетчера: «Не знаю заранее, где будет перегруз». Решает user story:
«Как диспетчер, я хочу получать предупреждение о риске переполнения за 30 минут, чтобы
заранее выпустить дополнительный вагон и не допустить сбоя в обслуживании».

Алерты — это **actionable** выход для операционного пользователя. Без них модель = «наблюдение»,
с ними = «управление».

## Acceptance Criteria

- [x] Endpoint `GET /api/v1/insights/alerts?window_min=30` (URL: see D-013, +insights/ prefix)
- [x] Возвращает список алертов: `[{stop_id, route_id, predicted_load_pct, time_to_overload_min, severity}]`
- [x] Severity: warning (90-110%), critical (>110%), info (75-90%)
- [x] Polling каждые 60 сек в UI (setInterval via TanStack Query, see D-013)
- [x] Карточка алерта в UI: route_name + stop_id + ETA до перегруза + кнопка «Выпустить вагон»
- [x] Сортировка по severity (critical → warning → info), затем по ETA ascending
- [x] При отсутствии алертов — `✅ Всё в норме на ближайшие 30 мин`
- [x] Unit-тесты: `test_find_overload_alerts.py` (16 кейсов) + `test_alerts_endpoint.py` (5 кейсов)

## Technical Notes

Использует существующий `apps/backend/app/api/predictions.py` как базу для прогноза загрузки.
Добавляет:
1. Time-to-overload: `t_peak - t_now` в минутах
2. Severity classification
3. UI с auto-refresh

В `apps/streamlit_app/app.py`:
```python
if mode == "🎛️ Диспетчер":
    st_autorefresh(interval=60_000, key="alerts_refresh")
    alerts = fetch_alerts(horizon_min=30)
    for alert in alerts:
        if alert.severity == "critical":
            st.error(f"🚨 {alert.route_name}: перегруз через {alert.minutes} мин")
        elif alert.severity == "warning":
            st.warning(f"⚠️ {alert.route_name}: близко к перегрузу")
```

## Verification

```bash
# Backend
curl "http://localhost:8000/api/v1/alerts/overload?horizon_min=30" | jq
# Должен вернуть массив алертов

# UI smoke
streamlit run apps/streamlit_app/app.py
# Режим "Диспетчер" → должны появиться карточки алертов
# Auto-refresh каждые 60 сек
```

## Beneficiary Impact

**Диспетчеры (⭐⭐⭐⭐⭐)** — главный инструмент оперативного реагирования.
**Пассажиры (⭐⭐⭐⭐)** — косвенно: предотвращение перегруза = комфортная поездка.
**Департамент** — демонстрация production-ready системы управления.

RICE: 8.1 — топ-9. Делается в Фазе 1-2.
