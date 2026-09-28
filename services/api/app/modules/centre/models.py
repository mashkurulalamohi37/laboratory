"""Branches, processing labs, patient-facing centres, opening hours and holidays."""

from __future__ import annotations

import datetime as dt
import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "centre"

CENTRE_TYPES = ("BRANCH_CENTRE", "COLLECTION_POINT", "PARTNER")
#: Services a centre can advertise. Extend here (and in the web copy) as services launch.
CENTRE_SERVICES = (
    "SAMPLE_COLLECTION",
    "HOME_COLLECTION",
    "REPORT_DELIVERY",
    "ECG",
    "X_RAY",
    "ULTRASOUND",
    "DOCTOR_CHAMBER",
)


class Branch(TimestampMixin, Base):
    __tablename__ = "branches"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class Lab(TimestampMixin, Base):
    __tablename__ = "labs"
    __table_args__ = (Index("ix_labs_branch_id", "branch_id"), {"schema": SCHEMA})

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(150))
    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.branches.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class Centre(TimestampMixin, Base):
    __tablename__ = "centres"
    __table_args__ = (
        CheckConstraint(f"type IN {CENTRE_TYPES}", name="type_valid"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        Index("ix_centres_branch_id", "branch_id"),
        Index("ix_centres_district_id", "district_id"),
        Index("ix_centres_area_id", "area_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(150))
    type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="BRANCH_CENTRE")
    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.branches.id", ondelete="RESTRICT"), nullable=False
    )
    lab_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.labs.id", ondelete="RESTRICT")
    )
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    address_bn: Mapped[str | None] = mapped_column(String(300))
    landmark: Mapped[str | None] = mapped_column(String(200))
    district_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("geo.districts.id", ondelete="RESTRICT"), nullable=False
    )
    upazila_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("geo.upazilas.id", ondelete="RESTRICT")
    )
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("geo.areas.id", ondelete="RESTRICT")
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    phone: Mapped[str | None] = mapped_column(String(16))
    email: Mapped[str | None] = mapped_column(String(254))
    services: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, server_default=text("'{}'::varchar[]")
    )
    description: Mapped[str | None] = mapped_column(Text)
    description_bn: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    hours: Mapped[list[CentreHours]] = relationship(
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="(CentreHours.weekday, CentreHours.opens_at)",
    )


Index(
    "ix_centres_name_trgm",
    func.lower(Centre.name).label("lower_name"),
    postgresql_using="gin",
    postgresql_ops={"lower_name": "gin_trgm_ops"},
)


class CentreHours(Base):
    """Weekly opening hours in Asia/Dhaka local time. `weekday`: 0 = Monday … 6 = Sunday.
    A day without rows is closed; several rows per day allow split shifts."""

    __tablename__ = "centre_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("opens_at < closes_at", name="opens_before_closes"),
        {"schema": SCHEMA},
    )

    centre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.centres.id", ondelete="CASCADE"), primary_key=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    opens_at: Mapped[time] = mapped_column(Time, primary_key=True)
    closes_at: Mapped[time] = mapped_column(Time, nullable=False)


class Holiday(TimestampMixin, Base):
    """Branch-wide closure (Eid dates vary by year, so they are data, not code)."""

    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("branch_id", "date", name="uq_holidays_branch_date"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.branches.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(150))
