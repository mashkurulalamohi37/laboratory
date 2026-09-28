"""Pydantic schemas for the sample module."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SampleRejectionReasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name_en: str
    name_bn: str
    requires_recollection: bool
    is_active: bool


class SampleEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sample_id: uuid.UUID
    event_type: str
    location_type: str
    location_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID | None = None
    notes: str | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime


class SampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    barcode: str
    booking_id: uuid.UUID
    booking_item_id: uuid.UUID | None = None
    patient_id: uuid.UUID
    sample_type_id: uuid.UUID
    container: str
    status: str
    collected_by: uuid.UUID | None = None
    collected_at: datetime | None = None
    collection_centre_id: uuid.UUID | None = None
    lab_id: uuid.UUID | None = None
    rejection_reason_id: uuid.UUID | None = None
    rejection_notes: str | None = None
    parent_sample_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    events: list[SampleEventOut] = Field(default_factory=list)


class SampleCreateRequest(BaseModel):
    booking_id: uuid.UUID
    booking_item_id: uuid.UUID | None = None
    patient_id: uuid.UUID
    sample_type_id: uuid.UUID
    container: str
    collection_centre_id: uuid.UUID | None = None
    lab_id: uuid.UUID | None = None


class SampleCollectRequest(BaseModel):
    sample_id: uuid.UUID
    container: str | None = None


class SampleReceiveRequest(BaseModel):
    barcodes: list[str]
    lab_id: uuid.UUID


class SampleRejectRequest(BaseModel):
    rejection_reason_id: uuid.UUID
    notes: str | None = None
    trigger_recollection: bool = True


class TransferCreateRequest(BaseModel):
    source_centre_id: uuid.UUID
    destination_lab_id: uuid.UUID
    sample_ids: list[uuid.UUID]
    temperature_celsius: float | None = None


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manifest_code: str
    source_centre_id: uuid.UUID
    destination_lab_id: uuid.UUID
    status: str
    dispatched_by: uuid.UUID
    dispatched_at: datetime
    received_by: uuid.UUID | None = None
    received_at: datetime | None = None
    temperature_celsius: float | None = None
    sample_count: int
    created_at: datetime
