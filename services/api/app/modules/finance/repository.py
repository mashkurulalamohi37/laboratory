"""Database access layer for finance expenses and AR/AP ledgers."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import ArApRecord, Expense


class FinanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_expense_by_id(self, expense_id: uuid.UUID) -> Expense | None:
        stmt = select(Expense).where(Expense.id == expense_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_expenses(
        self,
        category: str | None = None,
        centre_id: uuid.UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Sequence[Expense]:
        stmt = select(Expense).order_by(desc(Expense.expense_date))
        if category:
            stmt = stmt.where(Expense.category == category)
        if centre_id:
            stmt = stmt.where(Expense.centre_id == centre_id)
        if from_date:
            stmt = stmt.where(Expense.expense_date >= from_date)
        if to_date:
            stmt = stmt.where(Expense.expense_date <= to_date)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_ar_ap(
        self, record_type: str | None = None, status: str | None = None
    ) -> Sequence[ArApRecord]:
        stmt = select(ArApRecord).order_by(desc(ArApRecord.due_date))
        if record_type:
            stmt = stmt.where(ArApRecord.record_type == record_type)
        if status:
            stmt = stmt.where(ArApRecord.status == status)
        res = await self.session.execute(stmt)
        return res.scalars().all()
