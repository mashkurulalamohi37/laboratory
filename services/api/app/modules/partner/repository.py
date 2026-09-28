"""Repository for partner accounts, rules, and ledger queries."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.partner.models import CommissionEntry, CommissionRule, Partner


class PartnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, partner_id: uuid.UUID) -> Partner | None:
        stmt = (
            select(Partner)
            .where(Partner.id == partner_id)
            .options(selectinload(Partner.rules))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Partner | None:
        stmt = (
            select(Partner)
            .where(Partner.code == code)
            .options(selectinload(Partner.rules))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_partners(self, status: str | None = None) -> Sequence[Partner]:
        stmt = select(Partner).options(selectinload(Partner.rules))
        if status:
            stmt = stmt.where(Partner.status == status)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_rules(self, partner_id: uuid.UUID) -> Sequence[CommissionRule]:
        stmt = select(CommissionRule).where(
            CommissionRule.partner_id == partner_id,
            CommissionRule.is_active.is_(True),
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_entries(
        self, partner_id: uuid.UUID, status: str | None = None
    ) -> Sequence[CommissionEntry]:
        stmt = (
            select(CommissionEntry)
            .where(CommissionEntry.partner_id == partner_id)
            .order_by(desc(CommissionEntry.created_at))
        )
        if status:
            stmt = stmt.where(CommissionEntry.status == status)
        res = await self.session.execute(stmt)
        return res.scalars().all()
