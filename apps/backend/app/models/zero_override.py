"""ZeroOverride ORM model.

T-194: zero-strategy toggles (route 5, night hours, weekend, holidays).
Позволяет фронту показывать переключатели "с обнулением / без".

Privacy: no-PII.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ZeroOverride(Base):
    """Один override: zero_strategy + параметры."""

    __tablename__ = "zero_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    """zero_route_5 | zero_night_pred_cap | zero_weekend | zero_holidays"""
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    """{pred_cap: 55, hours: [0,1,2,3,4], ...}"""
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<ZeroOverride {self.name} enabled={self.enabled} params={self.params}>"
