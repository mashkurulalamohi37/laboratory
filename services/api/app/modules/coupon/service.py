"""Service for validating coupons and calculating discounts."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coupon.repository import CouponRepository
from app.modules.coupon.schemas import CouponValidateResponse


class CouponService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CouponRepository(session)

    async def validate_and_calculate(  # noqa: PLR0911
        self,
        *,
        code: str,
        user_id: uuid.UUID | None,
        subtotal: int,  # poisha
        is_first_booking: bool = False,
    ) -> CouponValidateResponse:
        coupon = await self.repo.get_by_code(code)
        if not coupon:
            return CouponValidateResponse(
                valid=False,
                code=code,
                discount_amount=0,
                message="Invalid or expired coupon code",
            )

        now = dt.datetime.now(dt.UTC)
        if coupon.starts_at > now or coupon.ends_at < now:
            return CouponValidateResponse(
                valid=False,
                code=code,
                discount_amount=0,
                message="This coupon is not active or has expired",
            )

        if subtotal < coupon.min_amount:
            min_tk = coupon.min_amount / 100
            return CouponValidateResponse(
                valid=False,
                code=code,
                discount_amount=0,
                message=f"Minimum order amount of ৳{min_tk:.0f} required for this coupon",
            )

        if coupon.first_booking_only and not is_first_booking:
            return CouponValidateResponse(
                valid=False,
                code=code,
                discount_amount=0,
                message="This coupon is only valid on your first booking",
            )

        if coupon.usage_limit is not None:
            total_uses = await self.repo.count_total_usages(coupon.id)
            if total_uses >= coupon.usage_limit:
                return CouponValidateResponse(
                    valid=False,
                    code=code,
                    discount_amount=0,
                    message="This coupon has reached its total usage limit",
                )

        if user_id:
            user_uses = await self.repo.count_user_usages(coupon.id, user_id)
            if user_uses >= coupon.per_user_limit:
                return CouponValidateResponse(
                    valid=False,
                    code=code,
                    discount_amount=0,
                    message="You have already used this coupon",
                )

        # Calculate discount
        if coupon.type == "PERCENT":
            # value is percentage (e.g. 10 = 10%)
            discount = (subtotal * coupon.value) // 100
            if coupon.max_discount is not None and discount > coupon.max_discount:
                discount = coupon.max_discount
        else:
            # FIXED poisha
            discount = min(subtotal, coupon.value)

        return CouponValidateResponse(
            valid=True,
            coupon_id=coupon.id,
            code=coupon.code,
            discount_amount=discount,
            message=f"Coupon {coupon.code} applied successfully!",
        )
