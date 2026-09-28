"""Pydantic schemas for coupons."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CouponType = Literal["PERCENT", "FIXED"]


class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    subtotal: int = Field(ge=0, description="Order subtotal in poisha")


class CouponValidateResponse(BaseModel):
    valid: bool
    coupon_id: uuid.UUID | None = None
    code: str
    discount_amount: int = 0  # in poisha
    message: str


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    type: str
    value: int
    max_discount: int | None = None
    min_amount: int
    starts_at: datetime
    ends_at: datetime
    is_active: bool
