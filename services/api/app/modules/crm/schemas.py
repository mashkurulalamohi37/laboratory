"""Pydantic schemas for CRM support tickets and threaded communication."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    patient_name: str
    phone: str
    category: str = "GENERAL"  # BOOKING, REPORT, COLLECTION, BILLING, GENERAL
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, URGENT
    subject: str
    description: str
    user_id: uuid.UUID | None = None


class TicketUpdate(BaseModel):
    status: str | None = None  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    priority: str | None = None
    assigned_to: uuid.UUID | None = None


class TicketMessageCreate(BaseModel):
    message: str


class TicketMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    is_staff: bool
    message: str
    created_at: datetime


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_no: str
    user_id: uuid.UUID | None = None
    patient_name: str
    phone: str
    category: str
    priority: str
    status: str
    subject: str
    description: str
    assigned_to: uuid.UUID | None = None
    sla_due_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    messages: list[TicketMessageOut] = Field(default_factory=list)
