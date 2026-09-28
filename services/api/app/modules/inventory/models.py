"""ORM models for inventory items, stock batches, movements, and purchase orders."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class InventoryItem(Base, TimestampMixin):
    """Catalog of consumable supplies, reagents, specimen containers, and kits."""

    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("code", name="uq_inventory_items_code"),
        Index("ix_inventory_items_category", "category"),
        {"schema": "inventory"},
    )

    id: Mapped[UUIDPk]
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)  # ITM-VAC-EDTA-3ML
    # category: REAGENT, CONSUMABLE, TUBE, KIT, PPE
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    # unit_of_measure: VIAL, BOX, PIECE, PACK, ML, TEST
    unit_of_measure: Mapped[str] = mapped_column(String(32), nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    cost_per_unit: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # Poisha
    centre_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    batches: Mapped[list[StockBatch]] = relationship(
        "StockBatch", back_populates="item", cascade="all, delete-orphan"
    )
    movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement", back_populates="item", cascade="all, delete-orphan"
    )


class StockBatch(Base, TimestampMixin):
    """Specific manufacturer batch with expiration date."""

    __tablename__ = "batches"
    __table_args__ = (
        Index("ix_stock_batches_item_id", "item_id"),
        Index("ix_stock_batches_expiry", "expiry_date"),
        {"schema": "inventory"},
    )

    id: Mapped[UUIDPk]
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory.items.id", ondelete="CASCADE"), nullable=False
    )
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="batches")


class StockMovement(Base, TimestampMixin):
    """Immutable audit ledger tracking inventory adjustments and consumptions."""

    __tablename__ = "movements"
    __table_args__ = (
        Index("ix_stock_movements_item_id", "item_id"),
        {"schema": "inventory"},
    )

    id: Mapped[UUIDPk]
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory.items.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("inventory.batches.id", ondelete="SET NULL"), nullable=True
    )
    # movement_type: IN, OUT, ADJUSTMENT, EXPIRED, DISCARDED
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # positive or negative delta
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="movements")


class PurchaseOrder(Base, TimestampMixin):
    """Institutional supply procurement order."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("po_number", name="uq_purchase_orders_po_number"),
        Index("ix_purchase_orders_status", "status"),
        {"schema": "inventory"},
    )

    id: Mapped[UUIDPk]
    po_number: Mapped[str] = mapped_column(String(32), nullable=False)  # PO-YYYY-NNNNNN
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # Poisha
    # status: DRAFT, ORDERED, RECEIVED, CANCELLED
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[PurchaseOrderItem]] = relationship(
        "PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base, TimestampMixin):
    """Line item in a purchase order."""

    __tablename__ = "purchase_order_items"
    __table_args__ = (
        Index("ix_purchase_order_items_po_id", "po_id"),
        {"schema": "inventory"},
    )

    id: Mapped[UUIDPk]
    po_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory.purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory.items.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # Poisha
    total_price: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    purchase_order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="items")
