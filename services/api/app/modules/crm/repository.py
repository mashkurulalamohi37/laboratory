"""Database access layer for CRM support tickets and messages."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.crm.models import SupportTicket


class CrmRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, ticket_id: uuid.UUID) -> SupportTicket | None:
        stmt = (
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id)
            .options(selectinload(SupportTicket.messages))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_tickets(
        self,
        status: str | None = None,
        category: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Sequence[SupportTicket]:
        stmt = (
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .order_by(desc(SupportTicket.created_at))
        )
        if status:
            stmt = stmt.where(SupportTicket.status == status)
        if category:
            stmt = stmt.where(SupportTicket.category == category)
        if user_id:
            stmt = stmt.where(SupportTicket.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()
