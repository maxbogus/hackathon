"""Events calendar (T-172): инфраструктурные открытия сентября-октября 2025.

Decay-weighted фичи для XGBoostRoutePredictor: 8 событий из
data/external/events_moscow.json, decay = exp(-Δt / τ_days).

API:
- load_events() -> list[dict] — читает JSON, валидирует schema
- get_event_features(date, route_id) -> dict[str, float] — 4 фичи для строки
- _decay(days_since, tau) -> float — экспоненциальный decay с клиппингом
- EVENT_FEATURE_NAMES — порядок имён фичей (для FEATURE_NAMES в xgboost_route)

R4 hackathon-rules: no internet at runtime.
R3 reproducible: JSON-каталог в data/external/.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

__all__ = [
    "EVENT_FEATURE_NAMES",
    "_decay",
    "get_event_features",
    "load_events",
]

# ────────────────────────────────────────────────────────────────────
# Расположение JSON-каталога
# ────────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVENTS_JSON = _REPO_ROOT / "data" / "external" / "events_moscow.json"
# Шаг 0 (T-231): нормализованный артефакт ETL; при наличии — приоритетный источник.
_EVENTS_NORMALIZED = _REPO_ROOT / "data" / "external" / "normalized" / "events.json"

# Порядок имён фичей для совместимости с FEATURE_NAMES в xgboost_route.py
EVENT_FEATURE_NAMES: tuple[str, ...] = (
    "event_metro_troitskaya_30d",
    "event_baumana_campus_30d",
    "event_route_90_active",
    "n_events_active_30d",
)

# Маппинг event_id → EVENT_FEATURE_NAMES (для 3 главных named фичей)
# 4-я фича (n_events_active_30d) — агрегат всех событий с весом > 0.5
_EVENT_TO_FEATURE: dict[str, str] = {
    "metro_troitskaya": "event_metro_troitskaya_30d",
    "bauman_campus": "event_baumana_campus_30d",
    "tram_route_90": "event_route_90_active",
}

# Threshold для "активного" события (decay > 0.5)
_ACTIVITY_THRESHOLD = 0.5


# ────────────────────────────────────────────────────────────────────
# Decay function
# ────────────────────────────────────────────────────────────────────


def _decay(days_since: float, tau: float) -> float:
    """Экспоненциальный decay: exp(-days_since / tau).

    Args:
        days_since: дней после события (отрицательное = событие ещё не было).
        tau: характерное время влияния (дни).

    Returns:
        float ∈ [0, 1]. Будущие события (days_since < 0) → 0 (нет утечки).
    """
    if days_since < 0:
        return 0.0
    return math.exp(-days_since / tau)


# ────────────────────────────────────────────────────────────────────
# JSON loader
# ────────────────────────────────────────────────────────────────────


def load_events() -> list[dict[str, Any]]:
    """Загрузить список событий из data/external/events_moscow.json.

    Returns:
        list[dict]: каждое событие имеет поля id, date, category, magnitude,
        tau_days, affected_routes, notes. date конвертируется из str в date.

    Raises:
        FileNotFoundError: если JSON не найден.
        ValueError: если schema невалидна (отсутствуют обязательные поля).
    """
    if _EVENTS_NORMALIZED.exists():
        payload = json.loads(_EVENTS_NORMALIZED.read_text(encoding="utf-8"))
        events_raw = payload.get("rows", [])
    else:
        if not _EVENTS_JSON.exists():
            raise FileNotFoundError(
                f"Events catalog not found: {_EVENTS_JSON}. "
                f"Expected: 8 events with id/date/category/magnitude/tau_days/"
                f"affected_routes/notes."
            )
        events_raw = json.loads(_EVENTS_JSON.read_text()).get("_events", [])

    required = {
        "id",
        "date",
        "category",
        "magnitude",
        "tau_days",
        "affected_routes",
        "notes",
    }
    events: list[dict[str, Any]] = []
    for ev in events_raw:
        missing = required - set(ev.keys())
        if missing:
            raise ValueError(f"Event {ev.get('id', '?')!r} missing fields: {missing}")
        # Конвертируем date из ISO-строки в date
        ev_copy = dict(ev)
        if isinstance(ev_copy["date"], str):
            ev_copy["date"] = date.fromisoformat(ev_copy["date"])
        events.append(ev_copy)

    return events


# ────────────────────────────────────────────────────────────────────
# Feature computation
# ────────────────────────────────────────────────────────────────────


def get_event_features(d: date, route_id: int) -> dict[str, float]:
    """Вычислить event-фичи для одной строки (date, route_id).

    Args:
        d: дата (submission или holdout).
        route_id: int маршрута (1, 5, 7, 11, 12, 17, 25, 26, 28, 50).

    Returns:
        dict с 4 ключами (EVENT_FEATURE_NAMES):
        - event_metro_troitskaya_30d: decay-weighted флаг для Троицкой
        - event_baumana_campus_30d: decay-weighted флаг для кампуса Бауманки
        - event_route_90_active: 0/1 флаг для нового маршрута №90
        - n_events_active_30d: count активных событий с decay > 0.5
    """
    # Инициализируем нулями
    feats: dict[str, float] = {name: 0.0 for name in EVENT_FEATURE_NAMES}

    n_active = 0
    for ev in load_events():
        # days_since: positive если событие уже было, negative если в будущем
        days_since = (d - ev["date"]).days
        if days_since < 0:
            continue  # событие ещё не произошло — flag = 0

        weight = _decay(float(days_since), float(ev["tau_days"]))
        if weight <= _ACTIVITY_THRESHOLD:
            # Слишком далеко по времени — игнорируем
            continue

        # Проверяем affected_routes: пусто = глобально, иначе маршрут должен быть в списке
        is_target = not ev["affected_routes"] or int(route_id) in ev["affected_routes"]

        if is_target:
            # Названная фича (для top-3 событий)
            feat_name = _EVENT_TO_FEATURE.get(ev["id"])
            if feat_name:
                # Берём max: если несколько событий маппятся на ту же фичу
                feats[feat_name] = max(feats[feat_name], weight)

            # Считаем в активные
            n_active += 1

    feats["n_events_active_30d"] = float(n_active)
    return feats
