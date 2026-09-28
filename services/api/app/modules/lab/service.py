"""Business logic for lab orders and worklists."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.modules.lab.models import (
    LabOrder,
    LabOrderItem,
    OrderItemStatus,
    OrderPriority,
    OrderStatus,
)
from app.modules.lab.repository import LabRepository
from app.modules.lab.schemas import LabOrderCreate


class LabService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = LabRepository(session)

    async def _generate_order_no(self) -> str:
        year = datetime.now(UTC).year
        count = await self._repo.count_orders_for_year(year)
        return f"LAB-{year}-{(count + 1):06d}"

    async def create_order(self, data: LabOrderCreate) -> LabOrder:
        order_no = await self._generate_order_no()
        order = LabOrder(
            order_no=order_no,
            booking_id=data.booking_id,
            patient_id=data.patient_id,
            lab_id=data.lab_id,
            status=OrderStatus.PENDING,
            priority=data.priority.upper() if data.priority else OrderPriority.ROUTINE,
            clinical_notes=data.clinical_notes,
        )
        saved = await self._repo.save_order(order)

        for item_data in data.items:
            item = LabOrderItem(
                lab_order_id=saved.id,
                booking_item_id=item_data.booking_item_id,
                test_id=item_data.test_id,
                sample_id=item_data.sample_id,
                department_id=item_data.department_id,
                status=OrderItemStatus.PENDING
                if not item_data.sample_id
                else OrderItemStatus.SAMPLE_LINKED,
            )
            await self._repo.save_item(item)

        return (await self._repo.get_order_by_id(saved.id)) or saved

    async def link_sample_to_item(self, item_id: uuid.UUID, sample_id: uuid.UUID) -> LabOrderItem:
        item = await self._repo.get_item_by_id(item_id)
        if not item:
            raise NotFound(code="LAB_ITEM_NOT_FOUND", message="Lab order item not found")
        item.sample_id = sample_id
        item.status = OrderItemStatus.SAMPLE_LINKED
        return await self._repo.save_item(item)

    async def get_order_by_id(self, order_id: uuid.UUID) -> LabOrder | None:
        return await self._repo.get_order_by_id(order_id)

    async def get_order_by_booking(self, booking_id: uuid.UUID) -> LabOrder | None:
        return await self._repo.get_order_by_booking(booking_id)

    async def get_item_by_id(self, item_id: uuid.UUID) -> LabOrderItem | None:
        return await self._repo.get_item_by_id(item_id)

    async def list_worklist(
        self,
        department_id: uuid.UUID | None = None,
        status: str | None = None,
        lab_id: uuid.UUID | None = None,
    ) -> Sequence[LabOrderItem]:
        return await self._repo.list_worklist_items(department_id, status, lab_id)
