"""Pydantic schemas for scheduling and slot availability."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SlotMode = Literal["HOME", "CENTRE"]
OwnerType = Literal["CENTRE", "ZONE"]


class SlotInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    date: date
    start_time: time
    end_time: time
    capacity: int
    booked: int
    held: int
    mode: str
    is_active: bool
    available: int = 0


class SlotHoldRequest(BaseModel):
    slot_id: uuid.UUID
    ttl_minutes: int = Field(default=10, ge=1, le=30)


class SlotHoldResponse(BaseModel):
    hold_id: uuid.UUID
    slot_id: uuid.UUID
    expires_at: datetime
    message: str = "Slot held successfully"
