"""SQLAlchemy models for corporate clients, contracts, and employee rosters."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    BigInteger,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class Corporate(Base, TimestampMixin):
    """B2B corporate client organization (e.g. Grameenphone, BAT, Brac)."""

    __tablename__ = "corporates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_corporates_code"),
        {"schema": "corporate"},
    )

    id: Mapped[UUIDPk]
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)  # CORP-XXX
    contact_person: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    credit_limit: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # Poisha
    credit_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    # Status: ACTIVE, SUSPENDED
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    contracts: Mapped[list[CorporateContract]] = relationship(
        "CorporateContract",
        back_populates="corporate",
        cascade="all, delete-orphan",
    )
    employees: Mapped[list[CorporateEmployee]] = relationship(
        "CorporateEmployee",
        back_populates="corporate",
        cascade="all, delete-orphan",
    )


class CorporateContract(Base, TimestampMixin):
    """Institutional discount contract, terms, and custom pricing."""

    __tablename__ = "corporate_contracts"
    __table_args__ = (
        Index("ix_corporate_contracts_corporate_id", "corporate_id"),
        {"schema": "corporate"},
    )

    id: Mapped[UUIDPk]
    corporate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("corporate.corporates.id", ondelete="CASCADE"), nullable=False
    )
    contract_code: Mapped[str] = mapped_column(String(64), nullable=False)
    price_list_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    # Status: ACTIVE, EXPIRED
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    corporate: Mapped[Corporate] = relationship("Corporate", back_populates="contracts")


class CorporateEmployee(Base, TimestampMixin):
    """Eligible employee enrolled in corporate diagnostics coverage."""

    __tablename__ = "corporate_employees"
    __table_args__ = (
        UniqueConstraint("corporate_id", "employee_code", name="uq_corporate_employees_code"),
        Index("ix_corporate_employees_corporate_id", "corporate_id"),
        Index("ix_corporate_employees_patient_id", "patient_id"),
        {"schema": "corporate"},
    )

    id: Mapped[UUIDPk]
    corporate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("corporate.corporates.id", ondelete="CASCADE"), nullable=False
    )
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Status: ACTIVE, INACTIVE
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    corporate: Mapped[Corporate] = relationship("Corporate", back_populates="employees")
