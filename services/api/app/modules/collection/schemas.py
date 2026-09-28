"""Pydantic schemas for the collection module."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CollectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    branch_id: uuid.UUID | None
    phone: str
    daily_capacity: int
    vehicle_type: str | None
    is_active: bool
    created_at: datetime


class CollectorCreate(BaseModel):
    user_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    phone: str
    daily_capacity: int = 15
    vehicle_type: str | None = None


class CollectionEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    status: str
    lat: float | None = None
    lng: float | None = None
    actor_user_id: uuid.UUID | None = None
    client_timestamp: datetime
    notes: str | None = None
    created_at: datetime


class CollectionAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    collector_id: uuid.UUID | None = None
    status: str
    scheduled_date: date
    slot_id: uuid.UUID | None = None
    verification_code: str
    accepted_at: datetime | None = None
    arrived_at: datetime | None = None
    patient_verified_at: datetime | None = None
    collected_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    events: list[CollectionEventOut] = Field(default_factory=list)


class AssignmentStatusUpdate(BaseModel):
    status: str  # ACCEPTED, ON_THE_WAY, ARRIVED, PATIENT_VERIFIED, COLLECTED, CANCELLED
    verification_code: str | None = None  # required when transitioning to PATIENT_VERIFIED
    lat: float | None = None
    lng: float | None = None
    client_timestamp: datetime | None = None
    notes: str | None = None


class ManualAssignRequest(BaseModel):
    booking_id: uuid.UUID
    collector_id: uuid.UUID
    scheduled_date: date
    slot_id: uuid.UUID | None = None
    notes: str | None = None


class AutoAssignRequest(BaseModel):
    target_date: date
    branch_id: uuid.UUID | None = None
