"""ORM models for the lab module."""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    SAMPLE_RECEIVED = "SAMPLE_RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderPriority(StrEnum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"


class OrderItemStatus(StrEnum):
    PENDING = "PENDING"
    SAMPLE_LINKED = "SAMPLE_LINKED"
    IN_TESTING = "IN_TESTING"
    RESULT_ENTERED = "RESULT_ENTERED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class LabOrder(Base, TimestampMixin):
    __tablename__ = "lab_orders"
    __table_args__ = (
        UniqueConstraint("order_no", name="uq_lab_orders_order_no"),
        {"schema": "lab"},
    )

    id: Mapped[UUIDPk]
    order_no: Mapped[str] = mapped_column(String(64), nullable=False)  # LAB-2026-000001
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("booking.bookings.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.patients.id", ondelete="CASCADE"), nullable=False
    )
    lab_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("centre.labs.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PENDING, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default=OrderPriority.ROUTINE, nullable=False)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[LabOrderItem]] = relationship(
        "LabOrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class LabOrderItem(Base, TimestampMixin):
    __tablename__ = "lab_order_items"
    __table_args__ = {"schema": "lab"}

    id: Mapped[UUIDPk]
    lab_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lab.lab_orders.id", ondelete="CASCADE"), nullable=False
    )
    booking_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("booking.booking_items.id", ondelete="SET NULL"), nullable=True
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("catalog.tests.id", ondelete="RESTRICT"), nullable=False
    )
    sample_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sample.samples.id", ondelete="SET NULL"), nullable=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("catalog.test_departments.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=OrderItemStatus.PENDING, nullable=False)

    order: Mapped[LabOrder] = relationship("LabOrder", back_populates="items")
