"""Bookings, items, and status transitions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "booking"

BOOKING_MODES = ("HOME", "CENTRE")
BOOKING_SOURCES = ("WEB", "CONSOLE", "PARTNER", "CORPORATE")
BOOKING_STATUSES = (
    "CREATED",
    "PAYMENT_PENDING",
    "CONFIRMED",
    "COLLECTOR_ASSIGNED",
    "COLLECTION_STARTED",
    "SAMPLE_COLLECTED",
    "LAB_RECEIVED",
    "PROCESSING",
    "RESULT_READY",
    "VERIFIED",
    "REPORT_GENERATED",
    "DELIVERED",
    "CANCELLED",
    "RESCHEDULED",
    "PAYMENT_FAILED",
    "REFUNDED",
)
ITEM_TYPES = ("TEST", "PACKAGE")


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("mode IN ('HOME', 'CENTRE')", name="ck_bookings_mode"),
        CheckConstraint(
            "source IN ('WEB', 'CONSOLE', 'PARTNER', 'CORPORATE')", name="ck_bookings_source"
        ),
        CheckConstraint("subtotal >= 0 AND total >= 0", name="ck_bookings_amounts"),
        CheckConstraint(
            "total = subtotal - discount + collection_fee", name="ck_bookings_total_equation"
        ),
        Index("ix_bookings_user_id", "user_id"),
        Index("ix_bookings_status", "status"),
        Index("ix_bookings_slot_id", "slot_id"),
        Index("ix_bookings_created_at", "created_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    booking_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="RESTRICT"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    centre_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("centre.centres.id", ondelete="SET NULL")
    )
    address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("patient.addresses.id", ondelete="SET NULL")
    )
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scheduling.slot_instances.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'CREATED'")
    )
    subtotal: Mapped[int] = mapped_column(BigInteger, nullable=False)  # poisha
    discount: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    collection_fee: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("coupon.coupons.id", ondelete="SET NULL")
    )
    partner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    corporate_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'WEB'"))
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    patient_notes: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    items: Mapped[list[BookingItem]] = relationship(
        "BookingItem", back_populates="booking", cascade="all, delete-orphan"
    )
    status_history: Mapped[list[BookingStatusHistory]] = relationship(
        "BookingStatusHistory", back_populates="booking", cascade="all, delete-orphan"
    )


class BookingItem(TimestampMixin, Base):
    __tablename__ = "booking_items"
    __table_args__ = (
        CheckConstraint("item_type IN ('TEST', 'PACKAGE')", name="ck_booking_items_type"),
        Index("ix_booking_items_booking_id", "booking_id"),
        Index("ix_booking_items_patient_id", "patient_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.bookings.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.patients.id", ondelete="RESTRICT"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    price_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)  # in poisha
    mrp_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)  # in poisha
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'PENDING'")
    )

    booking: Mapped[Booking] = relationship("Booking", back_populates="items")


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    __table_args__ = (
        Index("ix_booking_status_history_booking_id", "booking_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.bookings.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    booking: Mapped[Booking] = relationship("Booking", back_populates="status_history")
