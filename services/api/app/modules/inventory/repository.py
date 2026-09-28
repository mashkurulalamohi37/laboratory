"""Database access layer for inventory items, stock ledger, and purchase orders."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.inventory.models import (
    InventoryItem,
    PurchaseOrder,
    StockBatch,
    StockMovement,
)


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, item_id: uuid.UUID) -> InventoryItem | None:
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .options(selectinload(InventoryItem.batches))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, code: str) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.code == code)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_items(
        self, category: str | None = None, centre_id: uuid.UUID | None = None
    ) -> Sequence[InventoryItem]:
        stmt = select(InventoryItem).order_by(InventoryItem.name)
        if category:
            stmt = stmt.where(InventoryItem.category == category)
        if centre_id:
            stmt = stmt.where(InventoryItem.centre_id == centre_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_low_stock(self) -> Sequence[InventoryItem]:
        stmt = select(InventoryItem).where(
            InventoryItem.current_stock <= InventoryItem.reorder_level
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_movements(self, item_id: uuid.UUID) -> Sequence[StockMovement]:
        stmt = (
            select(StockMovement)
            .where(StockMovement.item_id == item_id)
            .order_by(desc(StockMovement.created_at))
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_batch_by_no(self, item_id: uuid.UUID, batch_no: str) -> StockBatch | None:
        stmt = select(StockBatch).where(
            StockBatch.item_id == item_id, StockBatch.batch_no == batch_no
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_purchase_orders(
        self, status: str | None = None
    ) -> Sequence[PurchaseOrder]:
        stmt = (
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.items))
            .order_by(desc(PurchaseOrder.created_at))
        )
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_po_by_id(self, po_id: uuid.UUID) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.items))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
