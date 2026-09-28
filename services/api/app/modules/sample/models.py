"""ORM models for the sample module."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class SampleStatus(StrEnum):
    CREATED = "CREATED"
    COLLECTED = "COLLECTED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    DISPOSED = "DISPOSED"


class TransferStatus(StrEnum):
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"


class SampleRejectionReason(Base):
    __tablename__ = "sample_rejection_reasons"
    __table_args__ = {"schema": "sample"}

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_bn: Mapped[str] = mapped_column(String(255), nullable=False)
    requires_recollection: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Sample(Base, TimestampMixin):
    __tablename__ = "samples"
    __table_args__ = (
        UniqueConstraint("barcode", name="uq_samples_barcode"),
        {"schema": "sample"},
    )

    id: Mapped[UUIDPk]
    barcode: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. SMP-2026-000001
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("booking.bookings.id", ondelete="CASCADE"), nullable=False
    )
    booking_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("booking.booking_items.id", ondelete="SET NULL"), nullable=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.patients.id", ondelete="CASCADE"), nullable=False
    )
    sample_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("catalog.sample_types.id", ondelete="RESTRICT"), nullable=False
    )
    container: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # e.g. "EDTA (Purple)", "Gel (Yellow)"
    status: Mapped[str] = mapped_column(String(32), default=SampleStatus.CREATED, nullable=False)

    collected_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collection_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("centre.centres.id", ondelete="SET NULL"), nullable=True
    )
    lab_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("centre.labs.id", ondelete="SET NULL"), nullable=True
    )

    rejection_reason_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sample.sample_rejection_reasons.id", ondelete="SET NULL"), nullable=True
    )
    rejection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sample.samples.id", ondelete="SET NULL"), nullable=True
    )

    events: Mapped[list[SampleEvent]] = relationship(
        "SampleEvent", back_populates="sample", cascade="all, delete-orphan"
    )


class SampleEvent(Base):
    __tablename__ = "sample_events"
    __table_args__ = {"schema": "sample"}

    id: Mapped[UUIDPk]
    sample_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sample.samples.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # CENTRE, LAB, TRANSIT, HOME
    location_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    sample: Mapped[Sample] = relationship("Sample", back_populates="events")


class SampleTransfer(Base, TimestampMixin):
    __tablename__ = "sample_transfers"
    __table_args__ = (
        UniqueConstraint("manifest_code", name="uq_sample_transfers_manifest"),
        {"schema": "sample"},
    )

    id: Mapped[UUIDPk]
    manifest_code: Mapped[str] = mapped_column(String(64), nullable=False)  # TRF-2026-000001
    source_centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("centre.centres.id", ondelete="RESTRICT"), nullable=False
    )
    destination_lab_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("centre.labs.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=TransferStatus.DISPATCHED, nullable=False
    )
    dispatched_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="RESTRICT"), nullable=False
    )
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    items: Mapped[list[SampleTransferItem]] = relationship(
        "SampleTransferItem", back_populates="transfer", cascade="all, delete-orphan"
    )


class SampleTransferItem(Base):
    __tablename__ = "sample_transfer_items"
    __table_args__ = (
        UniqueConstraint("transfer_id", "sample_id", name="uq_transfer_sample"),
        {"schema": "sample"},
    )

    id: Mapped[UUIDPk]
    transfer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sample.sample_transfers.id", ondelete="CASCADE"), nullable=False
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sample.samples.id", ondelete="CASCADE"), nullable=False
    )

    transfer: Mapped[SampleTransfer] = relationship("SampleTransfer", back_populates="items")
    sample: Mapped[Sample] = relationship("Sample")
