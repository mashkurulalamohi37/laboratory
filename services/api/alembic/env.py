"""Alembic environment (async). The database URL comes from application settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.models_registry  # noqa: F401  (register all models)
from app.core.config import get_settings
from app.core.db import MODULE_SCHEMAS, Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name, type_, parent_names):  # type: ignore[no-untyped-def]
    if type_ == "schema":
        return name in MODULE_SCHEMAS
    return True


def _configure(connection: Connection | None = None, url: str | None = None) -> None:
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="core",
        compare_type=True,
        compare_server_default=True,
    )


def run_migrations_offline() -> None:
    _configure(url=get_settings().database_url)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        # The version table lives in `core`, so the schema must exist first.
        await connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS core")
        await connection.commit()
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
