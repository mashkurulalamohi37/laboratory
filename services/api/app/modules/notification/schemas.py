"""Pydantic schemas for notification templates and dispatch history."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationTemplateCreate(BaseModel):
    code: str  # BOOKING_CONFIRMED, REPORT_READY, CRITICAL_ALERT
    channel: str = "SMS"  # SMS, EMAIL, PUSH
    language: str = "BN"  # EN, BN
    title: str | None = None
    body_template: str
    is_active: bool = True


class NotificationTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    channel: str
    language: str
    title: str | None = None
    body_template: str
    is_active: bool


class NotificationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient: str
    channel: str
    template_code: str
    status: str
    error_message: str | None = None
    dispatched_at: datetime
