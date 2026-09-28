"""Pydantic schemas for the lab module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LabOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lab_order_id: uuid.UUID
    booking_item_id: uuid.UUID | None = None
    test_id: uuid.UUID
    sample_id: uuid.UUID | None = None
    department_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class LabOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_no: str
    booking_id: uuid.UUID
    patient_id: uuid.UUID
    lab_id: uuid.UUID
    status: str
    priority: str
    clinical_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[LabOrderItemOut] = Field(default_factory=list)


class LabOrderCreate(BaseModel):
    booking_id: uuid.UUID
    patient_id: uuid.UUID
    lab_id: uuid.UUID
    priority: str = "ROUTINE"
    clinical_notes: str | None = None
    items: list[LabOrderItemCreate]


class LabOrderItemCreate(BaseModel):
    booking_item_id: uuid.UUID | None = None
    test_id: uuid.UUID
    sample_id: uuid.UUID | None = None
    department_id: uuid.UUID


class WorklistFilter(BaseModel):
    department_id: uuid.UUID | None = None
    status: str | None = None
    priority: str | None = None
    lab_id: uuid.UUID | None = None
