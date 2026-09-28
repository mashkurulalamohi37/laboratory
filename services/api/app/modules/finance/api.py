"""REST API routes for finance, operating expenses, and daily reconciliation."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.finance.schemas import (
    ArApRecordCreate,
    ArApRecordOut,
    ExpenseCreate,
    ExpenseOut,
    FinancialReconciliationOut,
)
from app.modules.finance.service import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> FinanceService:
    return FinanceService(session)


@router.post("/expenses", response_model=Envelope[ExpenseOut])
async def create_expense(
    data: ExpenseCreate,
    principal: Annotated[CurrentPrincipal, Depends(require(P.SETTINGS_MANAGE))],
    service: Annotated[FinanceService, Depends(get_service)],
) -> Envelope[ExpenseOut]:
    """Record an operational expense voucher."""
    expense = await service.create_expense(data, principal.user_id)
    return ok(expense)  # type: ignore[arg-type]


@router.get("/expenses", response_model=Envelope[list[ExpenseOut]])
async def list_expenses(
    _: Annotated[CurrentPrincipal, Depends(require(P.SETTINGS_MANAGE))],
    service: Annotated[FinanceService, Depends(get_service)],
    category: str | None = Query(None),
    centre_id: uuid.UUID | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> Envelope[list[ExpenseOut]]:
    """List expense vouchers."""
    items = await service.repo.list_expenses(category, centre_id, from_date, to_date)
    return ok(list(items))  # type: ignore[arg-type]


@router.get("/reconciliation", response_model=Envelope[FinancialReconciliationOut])
async def get_reconciliation(
    _: Annotated[CurrentPrincipal, Depends(require(P.SETTINGS_MANAGE))],
    service: Annotated[FinanceService, Depends(get_service)],
    target_date: date = Query(default_factory=date.today),
    centre_id: uuid.UUID | None = Query(None),
) -> Envelope[FinancialReconciliationOut]:
    """Calculate daily revenue and expense reconciliation."""
    recon = await service.get_reconciliation(target_date, centre_id)
    return ok(recon)


@router.post("/ar-ap", response_model=Envelope[ArApRecordOut])
async def create_ar_ap(
    data: ArApRecordCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.SETTINGS_MANAGE))],
    service: Annotated[FinanceService, Depends(get_service)],
) -> Envelope[ArApRecordOut]:
    """Create an accounts receivable or accounts payable record."""
    item = await service.create_ar_ap(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/ar-ap", response_model=Envelope[list[ArApRecordOut]])
async def list_ar_ap(
    _: Annotated[CurrentPrincipal, Depends(require(P.SETTINGS_MANAGE))],
    service: Annotated[FinanceService, Depends(get_service)],
    record_type: str | None = Query(None),
    status: str | None = Query(None),
) -> Envelope[list[ArApRecordOut]]:
    """List pending or settled AR/AP records."""
    items = await service.repo.list_ar_ap(record_type, status)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/ar-ap/{record_id}/settle", response_model=Envelope[ArApRecordOut])
async def settle_ar_ap(
    record_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.SETTINGS_MANAGE))],
    service: Annotated[FinanceService, Depends(get_service)],
) -> Envelope[ArApRecordOut]:
    """Mark an AR/AP item as settled."""
    item = await service.settle_ar_ap(record_id)
    return ok(item)  # type: ignore[arg-type]
