"""Public API of the audit module. Writes happen inside the caller's transaction, so an
action and its audit record commit (or roll back) together."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_request_context
from app.modules.audit.models import AuditLog

_SENSITIVE = ("password", "otp", "token", "secret", "hash")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _scrub(value)
    if isinstance(value, list | tuple | set | frozenset):
        return [_jsonable(v) for v in value]
    if isinstance(value, uuid.UUID | datetime | date | time | Decimal):
        return str(value)
    return value


def _scrub(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {
        key: "[REDACTED]" if any(s in key.lower() for s in _SENSITIVE) else _jsonable(value)
        for key, value in data.items()
    }


def record(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_roles: Iterable[str] = (),
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
) -> None:
    ctx = get_request_context()
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            actor_roles=sorted(set(actor_roles)),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            ip=ctx.ip if ctx else None,
            user_agent=ctx.user_agent if ctx else None,
            request_id=ctx.request_id if ctx else None,
            before=_scrub(before),
            after=_scrub(after),
        )
    )


async def search(
    session: AsyncSession,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[Sequence[AuditLog], int]:
    filters = []
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if action:
        filters.append(AuditLog.action == action)
    if since:
        filters.append(AuditLog.at >= since)
    if until:
        filters.append(AuditLog.at < until)

    total = (
        await session.execute(select(func.count()).select_from(AuditLog).where(*filters))
    ).scalar_one()
    rows = (
        (
            await session.execute(
                select(AuditLog)
                .where(*filters)
                .order_by(AuditLog.at.desc(), AuditLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return rows, int(total)
