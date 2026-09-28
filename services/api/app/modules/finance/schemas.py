"""Pydantic schemas for operating expenses, financial reconciliation, and AR/AP."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    category: str  # UTILITY, RENT, LOGISTICS, MAINTENANCE, SALARY, SUPPLIES, OTHER
    amount: int = Field(gt=0, description="Expense amount in BDT poisha")
    paid_to: str
    payment_method: str = "CASH"  # CASH, BANK, MFS
    expense_date: date
    centre_id: uuid.UUID | None = None
    notes: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    voucher_no: str
    category: str
    amount: int
    paid_to: str
    payment_method: str
    expense_date: date
    centre_id: uuid.UUID | None = None
    approved_by: uuid.UUID | None = None
    notes: str | None = None
    created_at: datetime


class ArApRecordCreate(BaseModel):
    record_type: str  # RECEIVABLE, PAYABLE
    party_name: str
    reference_id: str | None = None
    amount: int = Field(gt=0, description="Amount in BDT poisha")
    due_date: date
    notes: str | None = None


class ArApRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    record_type: str
    party_name: str
    reference_id: str | None = None
    amount: int
    due_date: date
    status: str
    settled_at: datetime | None = None
    notes: str | None = None
    created_at: datetime


class FinancialReconciliationOut(BaseModel):
    reconciliation_date: date
    centre_id: uuid.UUID | None = None
    total_revenue: int  # Gross booking & invoice collections in poisha
    total_expenses: int  # Total operating expenses in poisha
    net_operating_balance: int  # revenue - expenses
    expense_breakdown: dict[str, int]
    receivables_pending: int
    payables_pending: int
