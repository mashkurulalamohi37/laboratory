"""Business logic service for customer support tickets and SLA timers."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.ids import uuid7
from app.modules.crm.models import SupportTicket, TicketMessage
from app.modules.crm.repository import CrmRepository
from app.modules.crm.schemas import (
    TicketCreate,
    TicketMessageCreate,
    TicketUpdate,
)


class CrmService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CrmRepository(session)

    async def create_ticket(
        self, data: TicketCreate, user_id: uuid.UUID | None = None
    ) -> SupportTicket:
        year = datetime.now(UTC).year
        ticket_no = f"TCK-{year}-{secrets.randbelow(900000) + 100000}"

        # SLA calculation
        sla_hours = 24
        if data.priority == "URGENT":
            sla_hours = 2
        elif data.priority == "HIGH":
            sla_hours = 6
        elif data.priority == "LOW":
            sla_hours = 48
        sla_due_at = datetime.now(UTC) + timedelta(hours=sla_hours)

        ticket_id = uuid7()
        ticket = SupportTicket(
            id=ticket_id,
            ticket_no=ticket_no,
            user_id=user_id or data.user_id,
            patient_name=data.patient_name,
            phone=data.phone,
            category=data.category,
            priority=data.priority,
            status="OPEN",
            subject=data.subject,
            description=data.description,
            sla_due_at=sla_due_at,
        )
        self.session.add(ticket)

        # Initial message
        initial_msg = TicketMessage(
            id=uuid7(),
            ticket_id=ticket_id,
            sender_id=user_id or uuid7(),
            sender_name=data.patient_name,
            is_staff=False,
            message=data.description,
        )
        self.session.add(initial_msg)

        await self.session.commit()
        return await self.repo.get_by_id(ticket_id)  # type: ignore[return-value]

    async def add_message(
        self,
        ticket_id: uuid.UUID,
        data: TicketMessageCreate,
        sender_id: uuid.UUID,
        sender_name: str,
        is_staff: bool,
    ) -> TicketMessage:
        ticket = await self.repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFound(message="Support ticket not found")

        msg = TicketMessage(
            id=uuid7(),
            ticket_id=ticket.id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_staff=is_staff,
            message=data.message,
        )
        self.session.add(msg)

        if is_staff and ticket.status == "OPEN":
            ticket.status = "IN_PROGRESS"

        await self.session.commit()
        return msg

    async def update_ticket(
        self, ticket_id: uuid.UUID, data: TicketUpdate
    ) -> SupportTicket:
        ticket = await self.repo.get_by_id(ticket_id)
        if not ticket:
            raise NotFound(message="Support ticket not found")

        if data.status:
            ticket.status = data.status
            if data.status in ["RESOLVED", "CLOSED"]:
                ticket.resolved_at = datetime.now(UTC)
        if data.priority:
            ticket.priority = data.priority
        if data.assigned_to:
            ticket.assigned_to = data.assigned_to

        await self.session.commit()
        return ticket
