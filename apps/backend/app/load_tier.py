"""T-218: load_tier — маппинг load_pct -> tier.

Single source of truth: пороги должны ТОЧНО совпадать с apps/frontend/src/lib/loadTier.ts.
При изменении порогов — синхронизировать ОБА файла + обновить clinerule 31.

| load_pct | Tier     | Цвет (фронт) |
|----------|----------|---------------|
| < 70     | green    | комфортно    |
| 70..90   | yellow   | умеренно     |
| 90..110  | red      | тесно        |
| >= 110   | darkred  | перегруз     |
"""

from __future__ import annotations

from typing import Literal

LoadTier = Literal["green", "yellow", "red", "darkred"]


def compute_load_tier(load_pct: float) -> LoadTier:
    """Вычисляет tier по load_pct в процентах."""
    if load_pct < 70:
        return "green"
    if load_pct < 90:
        return "yellow"
    if load_pct < 110:
        return "red"
    return "darkred"


def compute_load_pct(boardings_avg: float, tram_capacity: int = 150) -> float:
    """load_pct = boardings_avg / tram_capacity * 100. Защита от деления на 0."""
    if tram_capacity <= 0:
        return 0.0
    return (boardings_avg / tram_capacity) * 100.0


__all__ = ["LoadTier", "compute_load_pct", "compute_load_tier"]
