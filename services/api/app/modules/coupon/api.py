"""FastAPI router for coupon validation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import OptionalPrincipal
from app.modules.coupon.schemas import (
    CouponValidateRequest,
    CouponValidateResponse,
)
from app.modules.coupon.service import CouponService

router = APIRouter(tags=["coupon"])


def get_coupon_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CouponService:
    return CouponService(session)


@router.post("/coupons/validate", response_model=Envelope[CouponValidateResponse])
async def validate_coupon(
    body: CouponValidateRequest,
    principal: OptionalPrincipal,
    service: Annotated[CouponService, Depends(get_coupon_service)],
) -> Envelope[CouponValidateResponse]:
    user_id = principal.user_id if principal else None
    res = await service.validate_and_calculate(
        code=body.code,
        user_id=user_id,
        subtotal=body.subtotal,
    )
    return ok(res)
