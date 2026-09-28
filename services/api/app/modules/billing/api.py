"""API routes for invoice creation, listing, and settlements."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.billing.schemas import InvoiceCreateRequest, InvoiceOut, InvoicePayRequest
from app.modules.billing.service import BillingService

router = APIRouter(prefix="/billing/invoices", tags=["Billing & Invoices"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> BillingService:
    return BillingService(session)


@router.post("", response_model=Envelope[InvoiceOut])
async def create_invoice(
    data: InvoiceCreateRequest,
    _: Annotated[CurrentPrincipal, Depends(require(P.INVOICE_MANAGE))],
    service: Annotated[BillingService, Depends(get_service)],
) -> Envelope[InvoiceOut]:
    """Issue a new invoice."""
    item = await service.create_invoice(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("", response_model=Envelope[list[InvoiceOut]])
async def list_invoices(
    _: Annotated[CurrentPrincipal, Depends(require(P.INVOICE_VIEW))],
    service: Annotated[BillingService, Depends(get_service)],
    bill_to_type: str | None = Query(None),
    corporate_id: uuid.UUID | None = Query(None),
    partner_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
) -> Envelope[list[InvoiceOut]]:
    """List invoices filtered by bill_to_type, status, or client."""
    items = await service.repo.list_invoices(
        bill_to_type=bill_to_type,
        corporate_id=corporate_id,
        partner_id=partner_id,
        status=status,
    )
    return ok(list(items))  # type: ignore[arg-type]


@router.get("/{invoice_id}", response_model=Envelope[InvoiceOut | None])
async def get_invoice(
    invoice_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.INVOICE_VIEW))],
    service: Annotated[BillingService, Depends(get_service)],
) -> Envelope[InvoiceOut | None]:
    item = await service.repo.get_by_id(invoice_id)
    return ok(item)  # type: ignore[arg-type]


@router.post("/{invoice_id}/pay", response_model=Envelope[InvoiceOut])
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    _: InvoicePayRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.INVOICE_MANAGE))],
    service: Annotated[BillingService, Depends(get_service)],
) -> Envelope[InvoiceOut]:
    """Mark an invoice settled / paid."""
    item = await service.settle_invoice(invoice_id)
    return ok(item)  # type: ignore[arg-type]
