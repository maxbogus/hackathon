"""Tests for events_calendar (T-172).

8 инфраструктурных событий сентября-октября 2025 (Троицкая, кампус Бауманки,
route 90, стадион Металлург, ТРЦ Краски, новые остановки, перенос платформ,
поликлиники). Decay-weighted фичи: `event_metro_troitskaya_30d`,
`event_baumana_campus_30d`, `event_route_90_active`, `n_events_active_30d`.
"""

from __future__ import annotations

from datetime import date

import pytest

from transit_ai.data.events_calendar import (
    EVENT_FEATURE_NAMES,
    _decay,
    get_event_features,
    load_events,
)

# ────────────────────────────────────────────────────────────────────
# Decay function
# ────────────────────────────────────────────────────────────────────


def test_decay_zero_at_event_date() -> None:
    """В день события days_since=0 → decay=exp(0)=1."""
    assert _decay(0.0, tau=30.0) == pytest.approx(1.0)


def test_decay_half_at_tau() -> None:
    """Через τ дней decay = exp(-1) ≈ 0.368."""
    assert _decay(30.0, tau=30.0) == pytest.approx(0.36787944117, rel=1e-6)


def test_decay_zero_for_future_event() -> None:
    """Если event ещё не произошёл — decay=0 (не утечка будущего)."""
    assert _decay(-5.0, tau=30.0) == 0.0


def test_decay_clipped_to_zero_for_old_event() -> None:
    """Через >5τ дней decay → ~0 (старое событие не влияет)."""
    assert _decay(180.0, tau=30.0) == pytest.approx(0.0025, abs=0.001)


# ────────────────────────────────────────────────────────────────────
# JSON catalog
# ────────────────────────────────────────────────────────────────────


def test_load_events_returns_at_least_8() -> None:
    """Каталог содержит ≥8 событий (T-172: 8 запланировано)."""
    events = load_events()
    assert len(events) >= 8, f"Expected ≥8 events, got {len(events)}"


def test_load_events_required_fields() -> None:
    """Каждое событие имеет обязательные поля."""
    required = {
        "id",
        "date",
        "category",
        "magnitude",
        "tau_days",
        "affected_routes",
        "notes",
    }
    for ev in load_events():
        missing = required - set(ev.keys())
        assert not missing, f"Event {ev.get('id', '?')!r} missing fields: {missing}"


def test_event_dates_in_2025() -> None:
    """Все события — в сентябре-октябре 2025 (или раньше, если есть)."""
    for ev in load_events():
        d = ev["date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        assert d.year == 2025, f"Event {ev['id']!r} not in 2025: {d}"


# ────────────────────────────────────────────────────────────────────
# Feature engineering
# ────────────────────────────────────────────────────────────────────


def test_event_feature_names_has_4_features() -> None:
    """4 фичи: 3 именованных + 1 агрегат (n_events_active_30d)."""
    assert len(EVENT_FEATURE_NAMES) == 4
    assert "n_events_active_30d" in EVENT_FEATURE_NAMES


def test_event_in_decay_window() -> None:
    """За 5 дней после события — flag > 0.5 (decay=exp(-5/30)≈0.85)."""
    # Берём кампус Бауманки (id='bauman_campus', date 2025-09-01)
    feats = get_event_features(date(2025, 9, 6), route_id=50)
    # Через 5 дней после event_date=01.09 → decay ≈ 0.85
    assert feats["event_baumana_campus_30d"] > 0.5
    assert feats["event_baumana_campus_30d"] < 1.0


def test_event_outside_decay_window() -> None:
    """Спустя >5τ дней — flag ≈ 0 (старое событие не влияет).

    Используем Троицкую (tau=60d), не кампус Бауманки (tau=365d, постоянный эффект).
    13.09.2025 + 365 = 13.09.2026 → exp(-365/60) ≈ 0.0023.
    """
    feats = get_event_features(date(2026, 9, 13), route_id=1)
    assert feats["event_metro_troitskaya_30d"] < 0.01


def test_event_route_targeting() -> None:
    """Событие affected_routes=[50] — flag > 0 для route 50, = 0 для route 25."""
    # На 10 дней после открытия кампуса (01.09 → 11.09)
    d = date(2025, 9, 11)
    feats_50 = get_event_features(d, route_id=50)
    feats_25 = get_event_features(d, route_id=25)
    assert feats_50["event_baumana_campus_30d"] > 0.5
    assert feats_25["event_baumana_campus_30d"] == 0.0


def test_event_global_applies_to_all_routes() -> None:
    """Глобальное событие (affected_routes=[]) — flag > 0 для любого route."""
    # Троицкая линия (id='metro_troitskaya', date 2025-09-13, affected=[])
    d = date(2025, 9, 20)  # 7 дней после открытия
    for route_id in (1, 5, 7, 11, 12, 17, 25, 26, 28, 50):
        feats = get_event_features(d, route_id=route_id)
        assert feats["event_metro_troitskaya_30d"] > 0.5, (
            f"Route {route_id}: expected metro_troitskaya > 0.5, "
            f"got {feats['event_metro_troitskaya_30d']}"
        )


def test_n_events_active_counts_correctly() -> None:
    """n_events_active_30d = count событий с decay > 0.5."""
    # 15 октября 2025 — 1.5 месяца после Троицкой (13.09),
    # ~1.5 месяца после кампуса Бауманки (01.09),
    # 30 дней после route 90 (15.09),
    # 4 дня после новых остановок (10.09) и 11.10 переноса платформ.
    d = date(2025, 10, 15)
    feats = get_event_features(d, route_id=50)
    assert feats["n_events_active_30d"] >= 2.0, (
        f"Expected ≥2 active events for route 50 on {d}, "
        f"got {feats['n_events_active_30d']}"
    )


def test_get_event_features_returns_all_keys() -> None:
    """Все EVENT_FEATURE_NAMES присутствуют в результате."""
    feats = get_event_features(date(2025, 9, 20), route_id=1)
    assert set(feats.keys()) == set(EVENT_FEATURE_NAMES)


def test_pre_event_date_returns_zeros() -> None:
    """До даты события — все флаги = 0 (нет утечки будущего)."""
    # Все события 2025 → на 01.01.2025 все флаги должны быть 0
    feats = get_event_features(date(2025, 1, 1), route_id=50)
    for k, v in feats.items():
        assert v == 0.0, f"Pre-event date: {k}={v} (expected 0)"
