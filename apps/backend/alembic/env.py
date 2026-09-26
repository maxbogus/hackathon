"""Alembic environment (async, SQLAlchemy 2.0).

Reads DATABASE_URL from env (TRANSIT_AI_DATABASE_URL) if set,
otherwise falls back to alembic.ini sqlalchemy.url.

Usage:
    # 1. Generate migration
    cd apps/backend
    uv run alembic revision --autogenerate -m "create predictions table"

    # 2. Apply migrations
    uv run alembic upgrade head

    # 3. Rollback
    uv run alembic downgrade -1
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Импорт Base + всех моделей (важно для autogenerate)
from app.models import Base

# Передаём sqlalchemy.url из env если задан
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url из env (TRANSIT_AI_DATABASE_URL)
import os

if db_url := os.environ.get("TRANSIT_AI_DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", db_url)
    # Если прислали async URL (asyncpg) для sqlite-теста, alembic падает.
    # Поддержим sync override через ALEMBIC_SYNC_DATABASE_URL.
    if db_url.startswith("sqlite") and "aiosqlite" not in db_url:
        # Преобразуем sqlite:///path → sqlite:///path (уже sync)
        pass
elif sync_url := os.environ.get("ALEMBIC_SYNC_DATABASE_URL"):
    # Sync override (например postgresql+psycopg2://)
    config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
