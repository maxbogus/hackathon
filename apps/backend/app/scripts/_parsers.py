"""Defensive CSV field parsers (T-198).

Каждый парсер возвращает None для пустых/мусорных значений вместо exceptions.
Это критично для seed скриптов — одна битая строка не должна валить весь seed.
"""

from __future__ import annotations

import re

# Регулярка для парсинга route_id: "25 трамвай" → 25.
# Берём только ведущие цифры, игнорируем хвост ("трамвай", "автобус").
_ROUTE_RE = re.compile(r"^\s*(\d+)")


def parse_route_id(raw: object) -> int | None:
    """Парсит поле ngpt_route из train.csv.

    Examples:
        >>> parse_route_id("25 трамвай")
        25
        >>> parse_route_id("трамвай")
        None
        >>> parse_route_id("")
        None
        >>> parse_route_id(None)
        None
    """
    if raw is None:
        return None
    m = _ROUTE_RE.match(str(raw))
    return int(m.group(1)) if m else None


def parse_int(raw: object) -> int | None:
    """Безопасный парсинг int, None если пусто/мусор."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_float(raw: object) -> float | None:
    """Безопасный парсинг float, None если пусто/мусор.

    Поддерживает comma-decimal ("3,14" → 3.14) для совместимости с locale.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


__all__ = ["parse_float", "parse_int", "parse_route_id"]
