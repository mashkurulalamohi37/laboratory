"""Repository for corporate accounts, contracts, and roster persistence."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.corporate.models import Corporate, CorporateEmployee


class CorporateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, corporate_id: uuid.UUID) -> Corporate | None:
        stmt = (
            select(Corporate)
            .where(Corporate.id == corporate_id)
            .options(selectinload(Corporate.contracts))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Corporate | None:
        stmt = (
            select(Corporate)
            .where(Corporate.code == code)
            .options(selectinload(Corporate.contracts))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_corporates(self, status: str | None = None) -> Sequence[Corporate]:
        stmt = select(Corporate).options(selectinload(Corporate.contracts))
        if status:
            stmt = stmt.where(Corporate.status == status)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_employees(self, corporate_id: uuid.UUID) -> Sequence[CorporateEmployee]:
        stmt = (
            select(CorporateEmployee)
            .where(CorporateEmployee.corporate_id == corporate_id)
            .order_by(CorporateEmployee.full_name)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_employee_by_code(
        self, corporate_id: uuid.UUID, employee_code: str
    ) -> CorporateEmployee | None:
        stmt = select(CorporateEmployee).where(
            CorporateEmployee.corporate_id == corporate_id,
            CorporateEmployee.employee_code == employee_code,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
