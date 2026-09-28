"""SQLAlchemy models for partners, commission rules, and ledger entries."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class Partner(Base, TimestampMixin):
    """External referral partners (clinics, hospitals, doctor networks, agents)."""

    __tablename__ = "partners"
    __table_args__ = (
        UniqueConstraint("code", name="uq_partners_code"),
        Index("ix_partners_status", "status"),
        {"schema": "partner"},
    )

    id: Mapped[UUIDPk]
    # partner_type: HOSPITAL, CLINIC, DOCTOR, AGENT
    partner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)  # PRT-XXX
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    centre_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Commission payout: MONTHLY, BIWEEKLY
    commission_payout_type: Mapped[str] = mapped_column(
        String(32), default="MONTHLY", nullable=False
    )
    # Status: ACTIVE, PENDING, SUSPENDED
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    rules: Mapped[list[CommissionRule]] = relationship(
        "CommissionRule",
        back_populates="partner",
        cascade="all, delete-orphan",
    )
    entries: Mapped[list[CommissionEntry]] = relationship(
        "CommissionEntry",
        back_populates="partner",
        cascade="all, delete-orphan",
    )


class CommissionRule(Base, TimestampMixin):
    """Rule determining commission rates for a partner."""

    __tablename__ = "commission_rules"
    __table_args__ = (
        Index("ix_commission_rules_partner_id", "partner_id"),
        {"schema": "partner"},
    )

    id: Mapped[UUIDPk]
    partner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("partner.partners.id", ondelete="CASCADE"), nullable=False
    )
    # Scope: ALL, CATEGORY, TEST, PACKAGE
    scope: Mapped[str] = mapped_column(String(32), default="ALL", nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Rule type: PERCENT, FIXED
    rule_type: Mapped[str] = mapped_column(String(32), default="PERCENT", nullable=False)
    value: Mapped[float] = mapped_column(Numeric(10, 2), default=10.0, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    partner: Mapped[Partner] = relationship("Partner", back_populates="rules")


class CommissionEntry(Base, TimestampMixin):
    """Immutable ledger entry for commission earned from a booking."""

    __tablename__ = "commission_entries"
    __table_args__ = (
        Index("ix_commission_entries_partner_id", "partner_id"),
        Index("ix_commission_entries_booking_id", "booking_id"),
        Index("ix_commission_entries_status", "status"),
        {"schema": "partner"},
    )

    id: Mapped[UUIDPk]
    partner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("partner.partners.id", ondelete="CASCADE"), nullable=False
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    gross_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # Poisha
    commission_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    net_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # Status: PENDING, APPROVED, PAID
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    partner: Mapped[Partner] = relationship("Partner", back_populates="entries")
