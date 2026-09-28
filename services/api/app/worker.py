"""Celery application: background jobs and periodic tasks (beat).

Queues: `critical` (OTP/critical alerts), `default` (notifications, outbox relay),
`reports` (PDF generation), `batch` (analytics, cleanup, expiry checks).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from celery import Celery
from kombu import Queue
from sqlalchemy import delete

from app.core.config import get_settings
from app.core.db import dispose_engine, get_sessionmaker
from app.core.logging import configure_logging, get_logger
from app.core.outbox import relay_batch

settings = get_settings()
configure_logging(settings.log_level, service="worker")
log = get_logger(__name__)

celery_app = Celery("nirnoy", broker=settings.broker_url)
celery_app.conf.update(
    task_default_queue="default",
    task_queues=[Queue("critical"), Queue("default"), Queue("reports"), Queue("batch")],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    timezone="Asia/Dhaka",
    enable_utc=True,
    beat_schedule={
        "outbox-relay": {"task": "core.relay_outbox", "schedule": 5.0},
        "auth-cleanup": {
            "task": "auth.cleanup_expired_tokens",
            "schedule": 6 * 3600.0,
            "options": {"queue": "batch"},
        },
    },
)


def run_async[T](fn: Callable[[], Awaitable[T]]) -> T:
    """Run a coroutine in a fresh event loop; the engine is disposed so pooled connections
    never cross loops."""

    async def _wrapped() -> T:
        try:
            return await fn()
        finally:
            await dispose_engine()

    return asyncio.run(_wrapped())


@celery_app.task(name="core.relay_outbox")
def relay_outbox() -> int:
    async def _run() -> int:
        async with get_sessionmaker()() as session, session.begin():
            return await relay_batch(session)

    return run_async(_run)


@celery_app.task(name="auth.cleanup_expired_tokens")
def cleanup_expired_tokens() -> int:
    from app.modules.auth.models import RefreshToken

    async def _run() -> int:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        async with get_sessionmaker()() as session, session.begin():
            result = await session.execute(
                delete(RefreshToken).where(RefreshToken.expires_at < cutoff)
            )
            return int(result.rowcount or 0)  # type: ignore[attr-defined]

    removed = run_async(_run)
    log.info("expired_refresh_tokens_removed", count=removed)
    return removed
