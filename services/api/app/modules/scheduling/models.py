"""Slot templates, slot instances and concurrency-safe holds."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "scheduling"

SLOT_MODES = ("HOME", "CENTRE")
SLOT_OWNER_TYPES = ("CENTRE", "ZONE")


class SlotTemplate(TimestampMixin, Base):
    __tablename__ = "slot_templates"
    __table_args__ = (
        CheckConstraint("mode IN ('HOME', 'CENTRE')", name="ck_slot_templates_mode"),
        CheckConstraint("owner_type IN ('CENTRE', 'ZONE')", name="ck_slot_templates_owner_type"),
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_slot_templates_weekday"),
        CheckConstraint("capacity > 0", name="ck_slot_templates_capacity"),
        Index("ix_slot_templates_owner", "owner_type", "owner_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("10"))
    mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'CENTRE'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class SlotInstance(TimestampMixin, Base):
    __tablename__ = "slot_instances"
    __table_args__ = (
        CheckConstraint("mode IN ('HOME', 'CENTRE')", name="ck_slot_instances_mode"),
        CheckConstraint("owner_type IN ('CENTRE', 'ZONE')", name="ck_slot_instances_owner_type"),
        CheckConstraint("booked >= 0 AND held >= 0", name="ck_slot_instances_counts"),
        CheckConstraint("booked + held <= capacity", name="ck_slot_instances_capacity"),
        UniqueConstraint(
            "owner_type",
            "owner_id",
            "date",
            "start_time",
            "mode",
            name="uq_slot_instances_owner_date_time_mode",
        ),
        Index("ix_slot_instances_date", "date"),
        Index("ix_slot_instances_owner", "owner_type", "owner_id", "date"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    booked: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    held: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    holds: Mapped[list[SlotHold]] = relationship(
        "SlotHold", back_populates="slot", cascade="all, delete-orphan"
    )


class SlotHold(TimestampMixin, Base):
    __tablename__ = "slot_holds"
    __table_args__ = (
        Index("ix_slot_holds_slot_id", "slot_id"),
        Index("ix_slot_holds_user_id", "user_id"),
        Index("ix_slot_holds_expires_at", "expires_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    slot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.slot_instances.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    slot: Mapped[SlotInstance] = relationship("SlotInstance", back_populates="holds")
