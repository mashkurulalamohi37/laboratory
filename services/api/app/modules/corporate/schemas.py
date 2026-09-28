"""Pydantic schemas for corporate accounts, contracts, and roster upload."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CorporateCreate(BaseModel):
    name: str
    contact_person: str
    contact_email: str
    contact_phone: str
    billing_address: str | None = None
    credit_limit: int = Field(default=0, ge=0, description="Credit limit in poisha")
    credit_days: int = Field(default=30, ge=0)


class CorporateContractCreate(BaseModel):
    contract_code: str
    price_list_id: uuid.UUID | None = None
    discount_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    valid_from: date
    valid_to: date


class CorporateContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    corporate_id: uuid.UUID
    contract_code: str
    price_list_id: uuid.UUID | None = None
    discount_percent: float
    valid_from: date
    valid_to: date
    status: str


class CorporateEmployeeCreate(BaseModel):
    employee_code: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    designation: str | None = None


class CorporateEmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    corporate_id: uuid.UUID
    employee_code: str
    patient_id: uuid.UUID | None = None
    full_name: str
    email: str | None = None
    phone: str | None = None
    designation: str | None = None
    status: str


class CorporateRosterUploadRequest(BaseModel):
    employees: list[CorporateEmployeeCreate]


class CorporateRosterUploadResult(BaseModel):
    added_count: int
    updated_count: int
    total_active: int


class CorporateMonthlyInvoiceRequest(BaseModel):
    billing_month: str = Field(description="YYYY-MM, e.g. 2026-09")
    due_days: int = 30


class CorporateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    contact_person: str
    contact_email: str
    contact_phone: str
    billing_address: str | None = None
    credit_limit: int
    credit_days: int
    status: str
    created_at: datetime
    contracts: list[CorporateContractOut] = Field(default_factory=list)
