"""Patients, family links, addresses and consents."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as sa_relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "patient"

SEX_TYPES = ("M", "F", "O")
BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
RELATIONSHIPS = ("SELF", "FATHER", "MOTHER", "SPOUSE", "CHILD", "SIBLING", "OTHER")
ADDRESS_LABELS = ("HOME", "WORK", "OTHER")


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("sex IN ('M', 'F', 'O')", name="ck_patients_sex"),
        CheckConstraint(
            "blood_group IS NULL OR blood_group IN "
            "('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')",
            name="ck_patients_blood_group",
        ),
        Index("ix_patients_owner_user_id", "owner_user_id"),
        Index("ix_patients_phone", "phone"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    patient_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    full_name_bn: Mapped[str | None] = mapped_column(String(150))
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(1), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    blood_group: Mapped[str | None] = mapped_column(String(5))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL")
    )

    family_links: Mapped[list[FamilyLink]] = sa_relationship(
        "FamilyLink", back_populates="patient", cascade="all, delete-orphan"
    )


class FamilyLink(TimestampMixin, Base):
    __tablename__ = "family_links"
    __table_args__ = (
        CheckConstraint(
            "relationship IN ('SELF', 'FATHER', 'MOTHER', 'SPOUSE', 'CHILD', 'SIBLING', 'OTHER')",
            name="ck_family_links_relationship",
        ),
        UniqueConstraint("user_id", "patient_id", name="uq_family_links_user_patient"),
        Index("ix_family_links_user_id", "user_id"),
        Index("ix_family_links_patient_id", "patient_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.patients.id", ondelete="CASCADE"), nullable=False
    )
    relationship: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'OTHER'")
    )

    patient: Mapped[Patient] = sa_relationship("Patient", back_populates="family_links")


class Address(TimestampMixin, Base):
    __tablename__ = "addresses"
    __table_args__ = (
        CheckConstraint("label IN ('HOME', 'WORK', 'OTHER')", name="ck_addresses_label"),
        Index("ix_addresses_user_id", "user_id"),
        Index("ix_addresses_patient_id", "patient_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.patients.id", ondelete="SET NULL")
    )
    division_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("geo.divisions.id", ondelete="SET NULL")
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("geo.districts.id", ondelete="SET NULL")
    )
    upazila_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("geo.upazilas.id", ondelete="SET NULL")
    )
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("geo.areas.id", ondelete="SET NULL")
    )
    house: Mapped[str] = mapped_column(String(100), nullable=False)
    road: Mapped[str | None] = mapped_column(String(100))
    block: Mapped[str | None] = mapped_column(String(50))
    landmark: Mapped[str | None] = mapped_column(String(150))
    label: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'HOME'"))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
