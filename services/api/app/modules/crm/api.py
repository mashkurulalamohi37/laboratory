"""REST API routes for CRM support tickets and customer messaging."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.crm.schemas import (
    TicketCreate,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketUpdate,
)
from app.modules.crm.service import CrmService

router = APIRouter(prefix="/crm", tags=["crm"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CrmService:
    return CrmService(session)


@router.post("/tickets", response_model=Envelope[TicketOut])
async def create_ticket(
    data: TicketCreate,
    principal: Annotated[CurrentPrincipal, Depends(require())],
    service: Annotated[CrmService, Depends(get_service)],
) -> Envelope[TicketOut]:
    """Create a new support or clinical inquiry ticket."""
    ticket = await service.create_ticket(data, principal.user_id)
    return ok(ticket)  # type: ignore[arg-type]


@router.get("/tickets", response_model=Envelope[list[TicketOut]])
async def list_tickets(
    principal: Annotated[CurrentPrincipal, Depends(require())],
    service: Annotated[CrmService, Depends(get_service)],
    status: str | None = Query(None),
    category: str | None = Query(None),
) -> Envelope[list[TicketOut]]:
    """List support tickets (staff sees all, patients see their own)."""
    user_id = None if principal.is_staff else principal.user_id
    items = await service.repo.list_tickets(status, category, user_id)
    return ok(list(items))  # type: ignore[arg-type]


@router.get("/tickets/{ticket_id}", response_model=Envelope[TicketOut | None])
async def get_ticket(
    ticket_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require())],
    service: Annotated[CrmService, Depends(get_service)],
) -> Envelope[TicketOut | None]:
    """Fetch ticket details and conversation thread."""
    item = await service.repo.get_by_id(ticket_id)
    return ok(item)  # type: ignore[arg-type]


@router.patch("/tickets/{ticket_id}", response_model=Envelope[TicketOut])
async def update_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdate,
    _: Annotated[CurrentPrincipal, Depends(require(P.SUPPORT_MANAGE))],
    service: Annotated[CrmService, Depends(get_service)],
) -> Envelope[TicketOut]:
    """Update ticket status, priority, or staff assignment."""
    item = await service.update_ticket(ticket_id, data)
    return ok(item)  # type: ignore[arg-type]


@router.post("/tickets/{ticket_id}/messages", response_model=Envelope[TicketMessageOut])
async def add_message(
    ticket_id: uuid.UUID,
    data: TicketMessageCreate,
    principal: Annotated[CurrentPrincipal, Depends(require())],
    service: Annotated[CrmService, Depends(get_service)],
) -> Envelope[TicketMessageOut]:
    """Post a reply to a support ticket thread."""
    sender_name = "Staff Member" if principal.is_staff else "Patient"
    msg = await service.add_message(
        ticket_id, data, principal.user_id, sender_name, principal.is_staff
    )
    return ok(msg)  # type: ignore[arg-type]
