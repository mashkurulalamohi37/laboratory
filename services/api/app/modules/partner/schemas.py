"""Pydantic schemas for partner referral networks, commission rules, and ledger statements."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PartnerCreate(BaseModel):
    partner_type: str = "CLINIC"  # HOSPITAL, CLINIC, DOCTOR, AGENT
    name: str
    phone: str
    email: str | None = None
    centre_id: uuid.UUID | None = None
    commission_payout_type: str = "MONTHLY"


class CommissionRuleCreate(BaseModel):
    partner_id: uuid.UUID
    scope: str = "ALL"  # ALL, CATEGORY, TEST, PACKAGE
    target_id: uuid.UUID | None = None
    rule_type: str = "PERCENT"  # PERCENT, FIXED
    value: float = Field(ge=0, description="Percent or fixed poisha")
    effective_from: date


class CommissionRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partner_id: uuid.UUID
    scope: str
    target_id: uuid.UUID | None = None
    rule_type: str
    value: float
    effective_from: date
    effective_to: date | None = None
    is_active: bool


class CommissionEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partner_id: uuid.UUID
    booking_id: uuid.UUID | None = None
    invoice_id: uuid.UUID | None = None
    gross_amount: int
    commission_amount: int
    net_amount: int
    status: str
    paid_at: datetime | None = None
    created_at: datetime


class PartnerStatementOut(BaseModel):
    partner_id: uuid.UUID
    partner_name: str
    partner_code: str
    period: str
    total_referrals: int
    gross_revenue: int
    earned_commission: int
    platform_net: int
    pending_commission: int
    paid_commission: int
    entries: list[CommissionEntryOut] = Field(default_factory=list)


class PartnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partner_type: str
    name: str
    code: str
    phone: str
    email: str | None = None
    centre_id: uuid.UUID | None = None
    commission_payout_type: str
    status: str
    created_at: datetime
    rules: list[CommissionRuleOut] = Field(default_factory=list)
