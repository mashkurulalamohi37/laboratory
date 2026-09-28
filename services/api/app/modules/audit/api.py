"""Read-only audit log access. There are deliberately no write/update/delete endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.responses import Envelope, ok
from app.modules.audit import service
from app.modules.auth.dependencies import require
from app.modules.auth.permissions import P
from app.modules.auth.principal import Principal

router = APIRouter(prefix="/admin/audit-logs", tags=["admin: audit"])


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    at: datetime
    actor_user_id: uuid.UUID | None
    actor_roles: list[str]
    action: str
    entity_type: str
    entity_id: str | None
    ip: str | None
    user_agent: str | None
    request_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None


@router.get(
    "",
    summary="Search the audit trail",
    description="Requires `audit:view`.",
    responses=error_responses(400, 401, 403),
)
async def list_audit_logs(
    _: Annotated[Principal, Depends(require(P.AUDIT_VIEW))],
    db: Annotated[AsyncSession, Depends(get_session)],
    entity_type: Annotated[str | None, Query(max_length=60)] = None,
    entity_id: Annotated[str | None, Query(max_length=64)] = None,
    actor_user_id: uuid.UUID | None = None,
    action: Annotated[str | None, Query(max_length=80)] = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Envelope[list[AuditLogOut]]:
    rows, total = await service.search(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
    )
    return ok(
        [AuditLogOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    )
