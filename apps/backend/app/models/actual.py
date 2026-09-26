"""Actual (historical boardings) ORM model.

T-194: хранит исторические данные по boardings (route × hour).
После alembic upgrade — будет конвертирована в TimescaleDB hypertable
для эффективных time-range queries (clinerule 18 DBML).

Privacy: no-PII.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Actual(Base):
    """Historical boardings (one row per route × datetime)."""

    __tablename__ = "actuals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)  # boardings

    __table_args__ = (
        Index("ix_actuals_route_period", "route_id", "period_start"),
    )

    def __repr__(self) -> str:
        return (
            f"<Actual route={self.route_id} t={self.period_start.isoformat()} "
            f"value={self.value:.0f}>"
        )
