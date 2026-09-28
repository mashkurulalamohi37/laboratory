"""Database engine, declarative base and per-request transactional session."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.config import get_settings
from app.core.ids import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

#: One PostgreSQL schema per module (see docs/architecture.md, ADR-5).
MODULE_SCHEMAS = (
    "core",
    "auth",
    "audit",
    "geo",
    "centre",
    "catalog",
    "cms",
    "patient",
    "scheduling",
    "coupon",
    "booking",
    "payment",
    "collection",
    "sample",
    "lab",
    "result",
    "report",
    "billing",
    "corporate",
    "partner",
    "inventory",
    "finance",
    "crm",
    "notification",
)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


UUIDPk = Annotated[uuid.UUID, mapped_column(Uuid, primary_key=True, default=uuid7)]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            connect_args={"server_settings": {"application_name": "nirnoy-api", "timezone": "UTC"}},
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one transaction per request.

    Commits when the endpoint returns normally and rolls back on any exception,
    including expected `AppError`s, so partial writes never persist.
    """
    async with get_sessionmaker()() as session:
        async with session.begin():
            yield session
        for callback in session.info.pop(_AFTER_COMMIT, []):
            await callback()


_AFTER_COMMIT = "after_commit"


def on_commit(session: AsyncSession, callback: Callable[[], Awaitable[None]]) -> None:
    """Run `callback` only after the request transaction commits (e.g. cache invalidation),
    so other requests cannot re-cache pre-commit state."""
    session.info.setdefault(_AFTER_COMMIT, []).append(callback)


@asynccontextmanager
async def independent_transaction() -> AsyncGenerator[AsyncSession]:
    """A separate transaction that commits even if the caller's request later fails.
    Use sparingly: security events that must persist (failed logins, token-reuse revocation)."""
    async with get_sessionmaker()() as session, session.begin():
        yield session


async def ping_database() -> bool:
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
