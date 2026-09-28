"""Payments, transactions, and webhook callbacks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "payment"

PAYMENT_METHODS = ("ONLINE", "CASH", "BKASH", "NAGAD", "CARD")
PAYMENT_PROVIDERS = ("SSLCOMMERZ", "CASH", "MANUAL")
PAYMENT_STATUSES = (
    "INITIATED",
    "PENDING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "REFUNDED",
    "PARTIALLY_REFUNDED",
)


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "method IN ('ONLINE', 'CASH', 'BKASH', 'NAGAD', 'CARD')",
            name="ck_payments_method",
        ),
        CheckConstraint(
            "provider IN ('SSLCOMMERZ', 'CASH', 'MANUAL')",
            name="ck_payments_provider",
        ),
        CheckConstraint(
            "status IN ('INITIATED', 'PENDING', 'SUCCEEDED', 'FAILED', "
            "'CANCELLED', 'REFUNDED', 'PARTIALLY_REFUNDED')",
            name="ck_payments_status",
        ),
        CheckConstraint("amount >= 0", name="ck_payments_amount"),
        Index("ix_payments_booking_id", "booking_id"),
        Index("ix_payments_status", "status"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("booking.bookings.id", ondelete="RESTRICT"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # poisha
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'INITIATED'")
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True)

    transactions: Mapped[list[PaymentTransaction]] = relationship(
        "PaymentTransaction", back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentTransaction(TimestampMixin, Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        Index("ix_payment_transactions_payment_id", "payment_id"),
        Index("ix_payment_transactions_provider_txn_id", "provider_txn_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.payments.id", ondelete="CASCADE"), nullable=False
    )
    provider_txn_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    payment: Mapped[Payment] = relationship("Payment", back_populates="transactions")


class PaymentCallback(TimestampMixin, Base):
    __tablename__ = "payment_callbacks"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_txn_id", "event_type", name="uq_payment_callbacks_txn_event"
        ),
        Index("ix_payment_callbacks_provider_txn_id", "provider_txn_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_txn_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
