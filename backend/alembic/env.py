import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

from alembic import context

from app.config import get_settings
from app.models import Base

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Set up Python logging from the ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support.
target_metadata = Base.metadata


def get_url() -> str:
    """Return the DB URL: prefer ALEMBIC_DATABASE_URL env var (for throwaway autogen),
    fall back to the app's settings-derived URL."""
    return os.getenv("ALEMBIC_DATABASE_URL") or get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    url = get_url()
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    def do_migrations(sync_conn) -> None:
        context.configure(
            connection=sync_conn,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    async def do_run() -> None:
        async with connectable.connect() as conn:
            await conn.run_sync(do_migrations)

    asyncio.run(do_run())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
