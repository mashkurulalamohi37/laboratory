"""API routes for partner network management, commission rules, and statements."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.partner.schemas import (
    CommissionRuleCreate,
    CommissionRuleOut,
    PartnerCreate,
    PartnerOut,
    PartnerStatementOut,
)
from app.modules.partner.service import PartnerService

router = APIRouter(prefix="/partner", tags=["Partner Network"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> PartnerService:
    return PartnerService(session)


@router.post("/partners", response_model=Envelope[PartnerOut])
async def create_partner(
    data: PartnerCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.PARTNER_MANAGE))],
    service: Annotated[PartnerService, Depends(get_service)],
) -> Envelope[PartnerOut]:
    """Register a new healthcare partner / referral network member."""
    item = await service.create_partner(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/partners", response_model=Envelope[list[PartnerOut]])
async def list_partners(
    _: Annotated[CurrentPrincipal, Depends(require(P.PARTNER_MANAGE))],
    service: Annotated[PartnerService, Depends(get_service)],
    status: str | None = Query(None),
) -> Envelope[list[PartnerOut]]:
    """List registered referral partners."""
    items = await service.repo.list_partners(status)
    return ok(list(items))  # type: ignore[arg-type]


@router.get("/partners/{partner_id}", response_model=Envelope[PartnerOut | None])
async def get_partner(
    partner_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.PARTNER_MANAGE))],
    service: Annotated[PartnerService, Depends(get_service)],
) -> Envelope[PartnerOut | None]:
    item = await service.repo.get_by_id(partner_id)
    return ok(item)  # type: ignore[arg-type]


@router.post("/rules", response_model=Envelope[CommissionRuleOut])
async def add_commission_rule(
    data: CommissionRuleCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.PARTNER_MANAGE))],
    service: Annotated[PartnerService, Depends(get_service)],
) -> Envelope[CommissionRuleOut]:
    """Configure custom commission percentage or fixed bounty for a partner."""
    item = await service.add_rule(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/partners/{partner_id}/statement", response_model=Envelope[PartnerStatementOut])
async def get_partner_statement(
    partner_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.PARTNER_MANAGE))],
    service: Annotated[PartnerService, Depends(get_service)],
    period: str = Query("current"),
) -> Envelope[PartnerStatementOut]:
    """Generate financial commission statement and payout ledger for a partner."""
    item = await service.generate_statement(partner_id, period)
    return ok(item)
