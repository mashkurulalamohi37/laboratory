"""ORM models for operating expenses, financial reconciliation, and AR/AP."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class Expense(Base, TimestampMixin):
    """Centre operational overhead, logistics, or utility disbursement."""

    __tablename__ = "expenses"
    __table_args__ = (
        UniqueConstraint("voucher_no", name="uq_expenses_voucher_no"),
        Index("ix_expenses_centre_id", "centre_id"),
        Index("ix_expenses_category", "category"),
        Index("ix_expenses_date", "expense_date"),
        {"schema": "finance"},
    )

    id: Mapped[UUIDPk]
    voucher_no: Mapped[str] = mapped_column(String(32), nullable=False)  # EXP-YYYY-NNNNNN
    # category: UTILITY, RENT, LOGISTICS, MAINTENANCE, SALARY, SUPPLIES, OTHER
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Poisha
    centre_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    paid_to: Mapped[str] = mapped_column(String(255), nullable=False)
    # payment_method: CASH, BANK, MFS
    payment_method: Mapped[str] = mapped_column(String(32), default="CASH", nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ArApRecord(Base, TimestampMixin):
    """Institutional accounts receivable and accounts payable ledger."""

    __tablename__ = "ar_ap_records"
    __table_args__ = (
        Index("ix_ar_ap_type", "record_type"),
        Index("ix_ar_ap_status", "status"),
        {"schema": "finance"},
    )

    id: Mapped[UUIDPk]
    # record_type: RECEIVABLE (owed to Nirnoy), PAYABLE (owed by Nirnoy)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    party_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Poisha
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    # status: PENDING, SETTLED, OVERDUE, CANCELLED
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
