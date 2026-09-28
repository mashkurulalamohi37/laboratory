"""Pydantic schemas for inventory management, stock batches, and purchase orders."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryItemCreate(BaseModel):
    name: str
    code: str
    category: str = "CONSUMABLE"  # REAGENT, CONSUMABLE, TUBE, KIT, PPE
    unit_of_measure: str = "PIECE"
    reorder_level: int = 50
    cost_per_unit: int = Field(default=0, ge=0, description="Cost per unit in BDT poisha")
    centre_id: uuid.UUID | None = None


class InventoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    category: str
    unit_of_measure: str
    current_stock: int
    reorder_level: int
    cost_per_unit: int
    centre_id: uuid.UUID | None = None
    created_at: datetime


class StockMovementCreate(BaseModel):
    item_id: uuid.UUID
    batch_no: str | None = None
    expiry_date: date | None = None
    movement_type: str  # IN, OUT, ADJUSTMENT, DISCARDED
    quantity: int
    reason: str | None = None


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    movement_type: str
    quantity: int
    reason: str | None = None
    actor_id: uuid.UUID
    created_at: datetime


class LowStockAlertOut(BaseModel):
    item_id: uuid.UUID
    item_name: str
    item_code: str
    category: str
    current_stock: int
    reorder_level: int
    deficit: int


class PurchaseOrderItemCreate(BaseModel):
    item_id: uuid.UUID
    quantity: int
    unit_price: int  # Poisha


class PurchaseOrderCreate(BaseModel):
    supplier_name: str
    notes: str | None = None
    items: list[PurchaseOrderItemCreate] = Field(default_factory=list)


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    quantity: int
    unit_price: int
    total_price: int


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    po_number: str
    supplier_name: str
    total_amount: int
    status: str
    ordered_at: datetime | None = None
    received_at: datetime | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemOut] = Field(default_factory=list)
    created_at: datetime
