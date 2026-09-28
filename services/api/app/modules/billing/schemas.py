"""Pydantic schemas for invoices and billing operations."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InvoiceItemCreate(BaseModel):
    description: str
    item_type: str = "TEST"
    item_id: uuid.UUID | None = None
    unit_price: int = Field(ge=0, description="Unit price in poisha")
    quantity: int = Field(default=1, ge=1)


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    description: str
    item_type: str
    item_id: uuid.UUID | None = None
    unit_price: int
    quantity: int
    total_amount: int


class InvoiceCreateRequest(BaseModel):
    bill_to_type: str = "PATIENT"  # PATIENT, CORPORATE, PARTNER
    bill_to_id: uuid.UUID
    bill_to_name: str
    booking_id: uuid.UUID | None = None
    corporate_id: uuid.UUID | None = None
    partner_id: uuid.UUID | None = None
    due_days: int = Field(default=15, ge=0)
    discount: int = Field(default=0, ge=0)
    tax: int = Field(default=0, ge=0)
    items: list[InvoiceItemCreate]


class InvoicePayRequest(BaseModel):
    notes: str | None = "Paid via bank/cash transfer"


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_no: str
    bill_to_type: str
    bill_to_id: uuid.UUID
    bill_to_name: str
    booking_id: uuid.UUID | None = None
    corporate_id: uuid.UUID | None = None
    partner_id: uuid.UUID | None = None
    subtotal: int
    discount: int
    tax: int
    total: int
    status: str
    due_date: date
    issued_at: datetime
    paid_at: datetime | None = None
    created_at: datetime
    items: list[InvoiceItemOut] = Field(default_factory=list)
