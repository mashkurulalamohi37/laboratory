"""ORM models for notification templates and dispatch history logs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDPk


class NotificationTemplate(Base, TimestampMixin):
    """Multi-channel, bilingual message templates for clinical & transactional events."""

    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint(
            "code", "channel", "language", name="uq_notification_templates_code_chan_lang"
        ),
        Index("ix_notification_templates_code", "code"),
        {"schema": "notification"},
    )

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    # channel: SMS, EMAIL, PUSH
    channel: Mapped[str] = mapped_column(String(32), default="SMS", nullable=False)
    # language: EN, BN
    language: Mapped[str] = mapped_column(String(16), default="BN", nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class NotificationLog(Base, TimestampMixin):
    """Immutable audit trail of dispatched SMS, Email, and Push alerts."""

    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_notification_logs_recipient", "recipient"),
        Index("ix_notification_logs_status", "status"),
        {"schema": "notification"},
    )

    id: Mapped[UUIDPk]
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    template_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False)  # SENT, FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
