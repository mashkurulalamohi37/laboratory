"""Database repository for lab orders and worklists."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.lab.models import LabOrder, LabOrderItem


class LabRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_orders_for_year(self, year: int) -> int:
        stmt = select(func.count(LabOrder.id))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def save_order(self, order: LabOrder) -> LabOrder:
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_order_by_id(self, order_id: uuid.UUID) -> LabOrder | None:
        stmt = select(LabOrder).options(selectinload(LabOrder.items)).where(LabOrder.id == order_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_order_by_booking(self, booking_id: uuid.UUID) -> LabOrder | None:
        stmt = (
            select(LabOrder)
            .options(selectinload(LabOrder.items))
            .where(LabOrder.booking_id == booking_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_item_by_id(self, item_id: uuid.UUID) -> LabOrderItem | None:
        stmt = select(LabOrderItem).where(LabOrderItem.id == item_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_item(self, item: LabOrderItem) -> LabOrderItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_worklist_items(
        self,
        department_id: uuid.UUID | None = None,
        status: str | None = None,
        lab_id: uuid.UUID | None = None,
    ) -> Sequence[LabOrderItem]:
        stmt = select(LabOrderItem).join(LabOrder)
        if department_id:
            stmt = stmt.where(LabOrderItem.department_id == department_id)
        if status:
            stmt = stmt.where(LabOrderItem.status == status)
        if lab_id:
            stmt = stmt.where(LabOrder.lab_id == lab_id)
        stmt = stmt.order_by(LabOrderItem.created_at.asc())
        result = await self._session.execute(stmt)
        return result.scalars().all()
