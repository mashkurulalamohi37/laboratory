"""SQLAlchemy models for invoices and billing line items."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class Invoice(Base, TimestampMixin):
    """Financial invoice billed to patients, corporate clients, or partners."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_no", name="uq_invoices_invoice_no"),
        Index("ix_invoices_bill_to", "bill_to_type", "bill_to_id"),
        Index("ix_invoices_corporate_id", "corporate_id"),
        Index("ix_invoices_partner_id", "partner_id"),
        Index("ix_invoices_status", "status"),
        {"schema": "billing"},
    )

    id: Mapped[UUIDPk]
    invoice_no: Mapped[str] = mapped_column(String(32), nullable=False)  # INV-YYYY-NNNNNN
    # bill_to_type: PATIENT, CORPORATE, PARTNER
    bill_to_type: Mapped[str] = mapped_column(String(32), nullable=False)
    bill_to_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    bill_to_name: Mapped[str] = mapped_column(String(255), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    corporate_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    partner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Subtotal stored in poisha (1/100 BDT)
    subtotal: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    discount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Status: DRAFT, ISSUED, PAID, CANCELLED, OVERDUE
    status: Mapped[str] = mapped_column(String(32), default="ISSUED", nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list[InvoiceItem]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class InvoiceItem(Base, TimestampMixin):
    """Individual line item on an invoice."""

    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("ix_invoice_items_invoice_id", "invoice_id"),
        {"schema": "billing"},
    )

    id: Mapped[UUIDPk]
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("billing.invoices.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    # item_type: TEST, PACKAGE, SERVICE, FEE
    item_type: Mapped[str] = mapped_column(String(32), default="TEST", nullable=False)
    item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    unit_price: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="items")
