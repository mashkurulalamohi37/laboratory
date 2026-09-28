"""Database repository for coupon module."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coupon.models import Coupon, CouponUsage


class CouponRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code(self, code: str) -> Coupon | None:
        query = select(Coupon).where(
            func.upper(Coupon.code) == code.strip().upper(),
            Coupon.is_active.is_(True),
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_id(self, coupon_id: uuid.UUID) -> Coupon | None:
        query = select(Coupon).where(Coupon.id == coupon_id)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def count_total_usages(self, coupon_id: uuid.UUID) -> int:
        query = select(func.count(CouponUsage.id)).where(CouponUsage.coupon_id == coupon_id)
        return (await self.session.execute(query)).scalar_one()

    async def count_user_usages(self, coupon_id: uuid.UUID, user_id: uuid.UUID) -> int:
        query = select(func.count(CouponUsage.id)).where(
            CouponUsage.coupon_id == coupon_id,
            CouponUsage.user_id == user_id,
        )
        return (await self.session.execute(query)).scalar_one()

    async def record_usage(
        self,
        *,
        coupon_id: uuid.UUID,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: int,
    ) -> CouponUsage:
        usage = CouponUsage(
            coupon_id=coupon_id,
            booking_id=booking_id,
            user_id=user_id,
            amount=amount,
        )
        self.session.add(usage)
        await self.session.flush()
        return usage
