"""ORM models for the result module."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class ResultStatus(StrEnum):
    DRAFT = "DRAFT"
    ENTERED = "ENTERED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    RETURNED = "RETURNED"
    AMENDED = "AMENDED"


class ResultFlag(StrEnum):
    N = "N"  # Normal
    L = "L"  # Low
    H = "H"  # High
    CL = "CL"  # Critical Low
    CH = "CH"  # Critical High
    ABN = "ABN"  # Abnormal text result


class AlertStatus(StrEnum):
    TRIGGERED = "TRIGGERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Result(Base, TimestampMixin):
    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("lab_order_item_id", "version", name="uq_result_item_version"),
        {"schema": "result"},
    )

    id: Mapped[UUIDPk]
    lab_order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lab.lab_order_items.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=ResultStatus.DRAFT, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    amended_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    amended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amend_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    parameters: Mapped[list[ResultParameter]] = relationship(
        "ResultParameter", back_populates="result", cascade="all, delete-orphan"
    )
    comments: Mapped[list[ResultComment]] = relationship(
        "ResultComment", back_populates="result", cascade="all, delete-orphan"
    )


class ResultParameter(Base):
    __tablename__ = "result_parameters"
    __table_args__ = {"schema": "result"}

    id: Mapped[UUIDPk]
    result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("result.results.id", ondelete="CASCADE"), nullable=False
    )
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("catalog.test_parameters.id", ondelete="RESTRICT"), nullable=False
    )
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_option: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_range_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    flag: Mapped[str] = mapped_column(String(16), default=ResultFlag.N, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delta_check_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    result: Mapped[Result] = relationship("Result", back_populates="parameters")


class ResultComment(Base):
    __tablename__ = "result_comments"
    __table_args__ = {"schema": "result"}

    id: Mapped[UUIDPk]
    result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("result.results.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="RESTRICT"), nullable=False
    )
    comment_type: Mapped[str] = mapped_column(
        String(32), default="CLINICAL", nullable=False
    )  # INTERNAL, CLINICAL, METHODOLOGY
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    result: Mapped[Result] = relationship("Result", back_populates="comments")


class CriticalAlert(Base, TimestampMixin):
    __tablename__ = "critical_alerts"
    __table_args__ = {"schema": "result"}

    id: Mapped[UUIDPk]
    result_parameter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("result.result_parameters.id", ondelete="CASCADE"), nullable=False
    )
    lab_order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lab.lab_order_items.id", ondelete="CASCADE"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # CRITICAL_HIGH, CRITICAL_LOW, DELTA_CHECK
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=AlertStatus.TRIGGERED, nullable=False)
    notified_users: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
