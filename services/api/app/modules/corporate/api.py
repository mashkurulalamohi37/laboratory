"""API routes for corporate client accounts, roster uploads, and billing."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.billing.schemas import InvoiceOut
from app.modules.corporate.schemas import (
    CorporateContractCreate,
    CorporateContractOut,
    CorporateCreate,
    CorporateEmployeeOut,
    CorporateMonthlyInvoiceRequest,
    CorporateOut,
    CorporateRosterUploadRequest,
    CorporateRosterUploadResult,
)
from app.modules.corporate.service import CorporateService

router = APIRouter(prefix="/corporate", tags=["Corporate B2B"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CorporateService:
    return CorporateService(session)


@router.post("/clients", response_model=Envelope[CorporateOut])
async def create_corporate(
    data: CorporateCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.CORPORATE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
) -> Envelope[CorporateOut]:
    """Register a new corporate B2B client account."""
    item = await service.create_corporate(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/clients", response_model=Envelope[list[CorporateOut]])
async def list_corporates(
    _: Annotated[CurrentPrincipal, Depends(require(P.CORPORATE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
    status: str | None = Query(None),
) -> Envelope[list[CorporateOut]]:
    """List corporate institutional accounts."""
    items = await service.repo.list_corporates(status)
    return ok(list(items))  # type: ignore[arg-type]


@router.get("/clients/{corporate_id}", response_model=Envelope[CorporateOut | None])
async def get_corporate(
    corporate_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.CORPORATE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
) -> Envelope[CorporateOut | None]:
    item = await service.repo.get_by_id(corporate_id)
    return ok(item)  # type: ignore[arg-type]


@router.post("/clients/{corporate_id}/contracts", response_model=Envelope[CorporateContractOut])
async def add_contract(
    corporate_id: uuid.UUID,
    data: CorporateContractCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.CORPORATE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
) -> Envelope[CorporateContractOut]:
    item = await service.add_contract(corporate_id, data)
    return ok(item)  # type: ignore[arg-type]


@router.post(
    "/clients/{corporate_id}/employees/upload", response_model=Envelope[CorporateRosterUploadResult]
)
async def upload_roster(
    corporate_id: uuid.UUID,
    data: CorporateRosterUploadRequest,
    _: Annotated[CurrentPrincipal, Depends(require(P.CORPORATE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
) -> Envelope[CorporateRosterUploadResult]:
    """Bulk roster upload/sync of corporate eligible employees."""
    item = await service.upload_roster(corporate_id, data)
    return ok(item)


@router.get(
    "/clients/{corporate_id}/employees",
    response_model=Envelope[list[CorporateEmployeeOut]],
)
async def list_employees(
    corporate_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.CORPORATE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
) -> Envelope[list[CorporateEmployeeOut]]:
    items = await service.repo.list_employees(corporate_id)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/clients/{corporate_id}/invoices/monthly", response_model=Envelope[InvoiceOut])
async def generate_monthly_invoice(
    corporate_id: uuid.UUID,
    data: CorporateMonthlyInvoiceRequest,
    _: Annotated[CurrentPrincipal, Depends(require(P.INVOICE_MANAGE))],
    service: Annotated[CorporateService, Depends(get_service)],
) -> Envelope[InvoiceOut]:
    """Generate consolidated monthly invoice for corporate diagnostics utilization."""
    item = await service.generate_monthly_invoice(corporate_id, data)
    return ok(item)  # type: ignore[arg-type]
