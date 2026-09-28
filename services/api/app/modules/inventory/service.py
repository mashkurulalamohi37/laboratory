"""Business logic service for inventory management, stock ledger, and POs."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.core.ids import uuid7
from app.modules.inventory.models import (
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    StockBatch,
    StockMovement,
)
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import (
    InventoryItemCreate,
    LowStockAlertOut,
    PurchaseOrderCreate,
    StockMovementCreate,
)


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InventoryRepository(session)

    async def create_item(self, data: InventoryItemCreate) -> InventoryItem:
        existing = await self.repo.get_by_code(data.code)
        if existing:
            raise Conflict(message=f"Item with code {data.code} already exists")

        item = InventoryItem(
            id=uuid7(),
            name=data.name,
            code=data.code,
            category=data.category,
            unit_of_measure=data.unit_of_measure,
            current_stock=0,
            reorder_level=data.reorder_level,
            cost_per_unit=data.cost_per_unit,
            centre_id=data.centre_id,
        )
        self.session.add(item)
        await self.session.commit()
        return item

    async def record_movement(
        self, data: StockMovementCreate, actor_id: uuid.UUID
    ) -> StockMovement:
        item = await self.repo.get_by_id(data.item_id)
        if not item:
            raise NotFound(message="Inventory item not found")

        batch_id: uuid.UUID | None = None
        if data.batch_no:
            batch = await self.repo.get_batch_by_no(item.id, data.batch_no)
            if not batch and data.expiry_date:
                batch = StockBatch(
                    id=uuid7(),
                    item_id=item.id,
                    batch_no=data.batch_no,
                    expiry_date=data.expiry_date,
                    initial_quantity=data.quantity if data.quantity > 0 else 0,
                    remaining_quantity=data.quantity if data.quantity > 0 else 0,
                )
                self.session.add(batch)
            elif batch:
                batch.remaining_quantity = max(0, batch.remaining_quantity + data.quantity)
            if batch:
                batch_id = batch.id

        # Update item stock level
        item.current_stock = max(0, item.current_stock + data.quantity)

        movement = StockMovement(
            id=uuid7(),
            item_id=item.id,
            batch_id=batch_id,
            movement_type=data.movement_type,
            quantity=data.quantity,
            reason=data.reason,
            actor_id=actor_id,
        )
        self.session.add(movement)
        await self.session.commit()
        return movement

    async def get_low_stock_alerts(self) -> list[LowStockAlertOut]:
        items = await self.repo.list_low_stock()
        alerts: list[LowStockAlertOut] = []
        for itm in items:
            deficit = max(0, itm.reorder_level - itm.current_stock)
            alerts.append(
                LowStockAlertOut(
                    item_id=itm.id,
                    item_name=itm.name,
                    item_code=itm.code,
                    category=itm.category,
                    current_stock=itm.current_stock,
                    reorder_level=itm.reorder_level,
                    deficit=deficit,
                )
            )
        return alerts

    async def create_purchase_order(self, data: PurchaseOrderCreate) -> PurchaseOrder:
        year = datetime.now(UTC).year
        po_number = f"PO-{year}-{secrets.randbelow(900000) + 100000}"
        po_id = uuid7()

        total_amount = sum(i.quantity * i.unit_price for i in data.items)
        po = PurchaseOrder(
            id=po_id,
            po_number=po_number,
            supplier_name=data.supplier_name,
            total_amount=total_amount,
            status="ORDERED",
            ordered_at=datetime.now(UTC),
            notes=data.notes,
        )
        self.session.add(po)

        for item_in in data.items:
            po_item = PurchaseOrderItem(
                id=uuid7(),
                po_id=po_id,
                item_id=item_in.item_id,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
                total_price=item_in.quantity * item_in.unit_price,
            )
            self.session.add(po_item)

        await self.session.commit()
        return await self.repo.get_po_by_id(po_id)  # type: ignore[return-value]

    async def receive_purchase_order(
        self, po_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseOrder:
        po = await self.repo.get_po_by_id(po_id)
        if not po:
            raise NotFound(message="Purchase order not found")
        if po.status == "RECEIVED":
            raise Conflict(message="Purchase order has already been received")

        po.status = "RECEIVED"
        po.received_at = datetime.now(UTC)

        # Automatically credit inventory stock
        for item in po.items:
            inv_item = await self.repo.get_by_id(item.item_id)
            if inv_item:
                inv_item.current_stock += item.quantity
                movement = StockMovement(
                    id=uuid7(),
                    item_id=inv_item.id,
                    movement_type="IN",
                    quantity=item.quantity,
                    reason=f"Received PO #{po.po_number}",
                    actor_id=actor_id,
                )
                self.session.add(movement)

        await self.session.commit()
        return po
