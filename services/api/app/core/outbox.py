"""Transactional outbox: domain events are written in the same DB transaction as the
state change, then relayed asynchronously by a Celery task (see architecture ADR-8)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDPk
from app.core.logging import get_logger

log = get_logger(__name__)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_unpublished",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUIDPk]
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(String(500))


Handler = Callable[[dict[str, Any]], Awaitable[None]]
_handlers: dict[str, list[Handler]] = {}


def subscribe(topic: str) -> Callable[[Handler], Handler]:
    def decorator(fn: Handler) -> Handler:
        _handlers.setdefault(topic, []).append(fn)
        return fn

    return decorator


def emit(session: AsyncSession, topic: str, payload: dict[str, Any]) -> None:
    """Queue an event inside the caller's transaction."""
    session.add(OutboxEvent(topic=topic, payload=payload))


async def relay_batch(session: AsyncSession, *, batch_size: int = 100) -> int:
    """Deliver unpublished events to in-process handlers. Safe to run concurrently
    (rows are claimed with SKIP LOCKED). Handlers must be idempotent."""
    rows = (
        (
            await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None), OutboxEvent.attempts < 10)
                .order_by(OutboxEvent.created_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    for event in rows:
        try:
            for handler in _handlers.get(event.topic, []):
                await handler(event.payload)
            event.published_at = func.now()
        except Exception as exc:
            event.attempts += 1
            event.last_error = f"{type(exc).__name__}: {exc}"[:500]
            log.warning("outbox_handler_failed", topic=event.topic, event_id=str(event.id))
    return len(rows)
