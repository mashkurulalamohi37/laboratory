"""ORM models for the collection module."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class AssignmentStatus(StrEnum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    ON_THE_WAY = "ON_THE_WAY"
    ARRIVED = "ARRIVED"
    PATIENT_VERIFIED = "PATIENT_VERIFIED"
    COLLECTED = "COLLECTED"
    CANCELLED = "CANCELLED"


class Collector(Base, TimestampMixin):
    __tablename__ = "collectors"
    __table_args__ = {"schema": "collection"}

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("centre.branches.id", ondelete="SET NULL"), nullable=True
    )
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    daily_capacity: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    vehicle_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # BIKE, SCOOTER, PUBLIC
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    assignments: Mapped[list[CollectionAssignment]] = relationship(
        "CollectionAssignment", back_populates="collector"
    )


class CollectionAssignment(Base, TimestampMixin):
    __tablename__ = "collection_assignments"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_collection_assignment_booking"),
        {"schema": "collection"},
    )

    id: Mapped[UUIDPk]
    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("booking.bookings.id", ondelete="CASCADE"), nullable=False
    )
    collector_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("collection.collectors.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default=AssignmentStatus.PENDING, nullable=False
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("scheduling.slot_instances.id", ondelete="SET NULL"), nullable=True
    )
    verification_code: Mapped[str] = mapped_column(
        String(6), nullable=False
    )  # 4-6 digit code for patient verification
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    patient_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    collector: Mapped[Collector | None] = relationship("Collector", back_populates="assignments")
    events: Mapped[list[CollectionEvent]] = relationship(
        "CollectionEvent", back_populates="assignment", cascade="all, delete-orphan"
    )


class CollectionEvent(Base):
    __tablename__ = "collection_events"
    __table_args__ = {"schema": "collection"}

    id: Mapped[UUIDPk]
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("collection.collection_assignments.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    assignment: Mapped[CollectionAssignment] = relationship(
        "CollectionAssignment", back_populates="events"
    )
