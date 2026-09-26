"""FeatureToggle ORM model.

T-194: per-feature вкл/выкл + дефолты. Позволяет фронту показывать
checkbox toggles и сохранять состояние в БД (между сессиями пользователя).

Privacy: no-PII.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FeatureToggle(Base):
    """Один toggle: фича (например use_poi) включена или нет."""

    __tablename__ = "feature_toggles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    """use_poi | use_traffic | use_weather | use_events | use_seasonal | use_lag | ..."""
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Дефолтное состояние (используется для reset)."""
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<FeatureToggle {self.name} enabled={self.enabled}>"
