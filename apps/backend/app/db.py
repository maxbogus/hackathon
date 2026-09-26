"""Async SQLAlchemy session factory (T-195).

Используется как Depends в FastAPI эндпоинтах:
    async def get_actuals(..., session: AsyncSession = Depends(get_db)):
        ...

Конфигурация через TRANSIT_AI_DATABASE_URL (см. app.config.settings).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Singleton engine + sessionmaker (per process)
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            _get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI Depends для AsyncSession.

    Yields session, закрывает после запроса (даже при exception).
    """
    Session = _get_sessionmaker()
    async with Session() as session:
        yield session


async def dispose_engine() -> None:
    """Закрывает engine (для тестов / shutdown)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
