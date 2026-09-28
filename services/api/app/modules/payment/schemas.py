"""Pydantic schemas for payment initiation and verification."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

PaymentMethod = Literal["ONLINE", "CASH", "BKASH", "NAGAD", "CARD"]
PaymentProviderType = Literal["SSLCOMMERZ", "CASH", "MANUAL"]
PaymentStatus = Literal[
    "INITIATED", "PENDING", "SUCCEEDED", "FAILED", "CANCELLED", "REFUNDED", "PARTIALLY_REFUNDED"
]


class PaymentInitiateRequest(BaseModel):
    booking_id: uuid.UUID
    method: PaymentMethod = "ONLINE"
    provider: PaymentProviderType = "SSLCOMMERZ"
    idempotency_key: str | None = None


class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    amount: int  # poisha
    method: str
    provider: str
    status: str
    provider_txn_id: str
    redirect_url: str | None = None
    gateway_data: dict[str, Any] = {}


class PaymentCallbackPayload(BaseModel):
    provider: str
    provider_txn_id: str
    status: str
    amount: float | None = None
    val_id: str | None = None
    raw_payload: dict[str, Any] = {}


class PaymentVerifyResponse(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    status: str
    amount: int
    provider_txn_id: str
    verified_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    method: str
    provider: str
    amount: int
    status: str
    created_at: datetime
