"""Repository for billing queries and persistence."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.billing.models import Invoice


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(selectinload(Invoice.items))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_no(self, invoice_no: str) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(Invoice.invoice_no == invoice_no)
            .options(selectinload(Invoice.items))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_invoices(
        self,
        bill_to_type: str | None = None,
        bill_to_id: uuid.UUID | None = None,
        corporate_id: uuid.UUID | None = None,
        partner_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> Sequence[Invoice]:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.items))
            .order_by(desc(Invoice.issued_at))
        )
        if bill_to_type:
            stmt = stmt.where(Invoice.bill_to_type == bill_to_type)
        if bill_to_id:
            stmt = stmt.where(Invoice.bill_to_id == bill_to_id)
        if corporate_id:
            stmt = stmt.where(Invoice.corporate_id == corporate_id)
        if partner_id:
            stmt = stmt.where(Invoice.partner_id == partner_id)
        if status:
            stmt = stmt.where(Invoice.status == status)

        res = await self.session.execute(stmt)
        return res.scalars().all()
