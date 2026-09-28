"""REST API routes for notification templates and dispatch history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.notification.schemas import (
    NotificationLogOut,
    NotificationTemplateCreate,
    NotificationTemplateOut,
)
from app.modules.notification.service import NotificationManagementService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationManagementService:
    return NotificationManagementService(session)


@router.post("/templates", response_model=Envelope[NotificationTemplateOut])
async def create_template(
    data: NotificationTemplateCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.NOTIFICATION_MANAGE))],
    service: Annotated[NotificationManagementService, Depends(get_service)],
) -> Envelope[NotificationTemplateOut]:
    """Create or update a notification template."""
    item = await service.create_template(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/templates", response_model=Envelope[list[NotificationTemplateOut]])
async def list_templates(
    _: Annotated[CurrentPrincipal, Depends(require(P.NOTIFICATION_MANAGE))],
    service: Annotated[NotificationManagementService, Depends(get_service)],
    channel: str | None = Query(None),
) -> Envelope[list[NotificationTemplateOut]]:
    """List notification templates."""
    items = await service.list_templates(channel)
    return ok(list(items))  # type: ignore[arg-type]


@router.get("/history", response_model=Envelope[list[NotificationLogOut]])
async def list_history(
    _: Annotated[CurrentPrincipal, Depends(require(P.NOTIFICATION_MANAGE))],
    service: Annotated[NotificationManagementService, Depends(get_service)],
    channel: str | None = Query(None),
) -> Envelope[list[NotificationLogOut]]:
    """List recent notification dispatch audit logs."""
    items = await service.list_history(channel)
    return ok(list(items))  # type: ignore[arg-type]
