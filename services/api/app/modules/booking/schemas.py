"""Pydantic schemas for quotes and bookings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BookingMode = Literal["HOME", "CENTRE"]
ItemType = Literal["TEST", "PACKAGE"]


class CartItemInput(BaseModel):
    patient_id: uuid.UUID
    item_type: ItemType
    item_id: uuid.UUID


class QuoteRequest(BaseModel):
    mode: BookingMode
    centre_id: uuid.UUID | None = None
    address_id: uuid.UUID | None = None
    items: list[CartItemInput] = Field(min_length=1)
    coupon_code: str | None = None


class QuoteItemResponse(BaseModel):
    patient_id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    name: str
    price: int  # poisha
    mrp: int  # poisha


class QuoteResponse(BaseModel):
    subtotal: int  # poisha
    discount: int  # poisha
    collection_fee: int  # poisha
    total: int  # poisha
    coupon_applied: str | None = None
    items: list[QuoteItemResponse]


class BookingCreate(BaseModel):
    mode: BookingMode
    centre_id: uuid.UUID | None = None
    address_id: uuid.UUID | None = None
    slot_id: uuid.UUID
    items: list[CartItemInput] = Field(min_length=1)
    coupon_code: str | None = None
    patient_notes: str | None = None
    idempotency_key: str | None = None


class BookingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    name_snapshot: str
    price_snapshot: int
    mrp_snapshot: int
    status: str


class BookingStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: str | None = None
    to_status: str
    reason: str | None = None
    created_at: datetime


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_code: str
    user_id: uuid.UUID
    mode: str
    centre_id: uuid.UUID | None = None
    address_id: uuid.UUID | None = None
    slot_id: uuid.UUID | None = None
    status: str
    subtotal: int
    discount: int
    collection_fee: int
    total: int
    coupon_id: uuid.UUID | None = None
    source: str
    patient_notes: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    items: list[BookingItemResponse] = []
    status_history: list[BookingStatusHistoryResponse] = []


class BookingStatusUpdate(BaseModel):
    status: str
    reason: str | None = None


class BookingCancelRequest(BaseModel):
    reason: str | None = None
