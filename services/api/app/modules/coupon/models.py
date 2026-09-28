"""Coupons, rules, and usage records."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "coupon"

COUPON_TYPES = ("PERCENT", "FIXED")
COUPON_RULE_TYPES = ("TEST", "PACKAGE", "CENTRE", "CORPORATE", "USER", "CATEGORY")


class Coupon(TimestampMixin, Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("type IN ('PERCENT', 'FIXED')", name="ck_coupons_type"),
        CheckConstraint("value > 0", name="ck_coupons_value"),
        CheckConstraint("min_amount >= 0", name="ck_coupons_min_amount"),
        CheckConstraint(
            "max_discount IS NULL OR max_discount >= 0", name="ck_coupons_max_discount"
        ),
        Index("ix_coupons_code", "code"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)  # % (e.g. 10) or poisha
    max_discount: Mapped[int | None] = mapped_column(BigInteger)  # in poisha
    min_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    per_user_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    first_booking_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    usages: Mapped[list[CouponUsage]] = relationship(
        "CouponUsage", back_populates="coupon", cascade="all, delete-orphan"
    )


class CouponRule(TimestampMixin, Base):
    __tablename__ = "coupon_rules"
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('TEST', 'PACKAGE', 'CENTRE', 'CORPORATE', 'USER', 'CATEGORY')",
            name="ck_coupon_rules_type",
        ),
        Index("ix_coupon_rules_coupon_id", "coupon_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    coupon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.coupons.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class CouponUsage(TimestampMixin, Base):
    __tablename__ = "coupon_usage"
    __table_args__ = (
        UniqueConstraint("coupon_id", "booking_id", name="uq_coupon_usage_booking"),
        Index("ix_coupon_usage_coupon_user", "coupon_id", "user_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    coupon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.coupons.id", ondelete="RESTRICT"), nullable=False
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # discount given in poisha

    coupon: Mapped[Coupon] = relationship("Coupon", back_populates="usages")
