"""ORM models for customer support ticketing, threaded messaging, and SLA timers."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class SupportTicket(Base, TimestampMixin):
    """Customer service or clinical inquiry ticket."""

    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("ticket_no", name="uq_support_tickets_ticket_no"),
        Index("ix_support_tickets_status", "status"),
        Index("ix_support_tickets_category", "category"),
        Index("ix_support_tickets_user_id", "user_id"),
        {"schema": "crm"},
    )

    id: Mapped[UUIDPk]
    ticket_no: Mapped[str] = mapped_column(String(32), nullable=False)  # TCK-YYYY-NNNNNN
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    # category: BOOKING, REPORT, COLLECTION, BILLING, GENERAL
    category: Mapped[str] = mapped_column(String(32), default="GENERAL", nullable=False)
    # priority: LOW, NORMAL, HIGH, URGENT
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    # status: OPEN, IN_PROGRESS, RESOLVED, CLOSED
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[TicketMessage]] = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at.asc()",
    )


class TicketMessage(Base, TimestampMixin):
    """Threaded message reply in a support ticket."""

    __tablename__ = "ticket_messages"
    __table_args__ = (
        Index("ix_ticket_messages_ticket_id", "ticket_id"),
        {"schema": "crm"},
    )

    id: Mapped[UUIDPk]
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("crm.tickets.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    ticket: Mapped[SupportTicket] = relationship("SupportTicket", back_populates="messages")
