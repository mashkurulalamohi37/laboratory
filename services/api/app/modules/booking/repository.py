"""Database repository for booking module."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.booking.models import Booking, BookingItem, BookingStatusHistory


class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def next_booking_code(self) -> str:
        year = dt.datetime.now(dt.UTC).year
        prefix = f"BKG-{year}-"
        query = select(func.count(Booking.id)).where(Booking.booking_code.like(f"{prefix}%"))
        count = (await self.session.execute(query)).scalar_one()
        return f"{prefix}{count + 1:06d}"

    async def get_by_id(self, booking_id: uuid.UUID) -> Booking | None:
        query = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.items),
                selectinload(Booking.status_history),
            )
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Booking | None:
        query = (
            select(Booking)
            .where(Booking.idempotency_key == key)
            .options(
                selectinload(Booking.items),
                selectinload(Booking.status_history),
            )
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Booking]:
        query = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .options(
                selectinload(Booking.items),
                selectinload(Booking.status_history),
            )
            .order_by(Booking.created_at.desc())
        )
        return (await self.session.execute(query)).scalars().all()

    async def list_all(
        self,
        *,
        status: str | None = None,
        mode: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Booking]:
        query = (
            select(Booking)
            .options(
                selectinload(Booking.items),
                selectinload(Booking.status_history),
            )
            .order_by(Booking.created_at.desc())
        )
        if status:
            query = query.where(Booking.status == status)
        if mode:
            query = query.where(Booking.mode == mode)
        query = query.limit(limit).offset(offset)
        return (await self.session.execute(query)).scalars().all()

    async def count_all(
        self,
        *,
        status: str | None = None,
        mode: str | None = None,
    ) -> int:
        query = select(func.count(Booking.id))
        if status:
            query = query.where(Booking.status == status)
        if mode:
            query = query.where(Booking.mode == mode)
        return (await self.session.execute(query)).scalar_one()

    async def create_booking(
        self,
        *,
        user_id: uuid.UUID,
        mode: str,
        centre_id: uuid.UUID | None,
        address_id: uuid.UUID | None,
        slot_id: uuid.UUID | None,
        status: str,
        subtotal: int,
        discount: int,
        collection_fee: int,
        total: int,
        coupon_id: uuid.UUID | None,
        source: str = "WEB",
        idempotency_key: str | None = None,
        patient_notes: str | None = None,
    ) -> Booking:
        code = await self.next_booking_code()
        booking = Booking(
            booking_code=code,
            user_id=user_id,
            mode=mode,
            centre_id=centre_id,
            address_id=address_id,
            slot_id=slot_id,
            status=status,
            subtotal=subtotal,
            discount=discount,
            collection_fee=collection_fee,
            total=total,
            coupon_id=coupon_id,
            source=source,
            idempotency_key=idempotency_key,
            patient_notes=patient_notes,
            version=1,
        )
        self.session.add(booking)
        await self.session.flush()

        # Record initial status in history
        history = BookingStatusHistory(
            booking_id=booking.id,
            from_status=None,
            to_status=status,
            actor_user_id=user_id,
            reason="Booking created",
        )
        self.session.add(history)
        await self.session.flush()
        return booking

    async def add_item(
        self,
        *,
        booking_id: uuid.UUID,
        patient_id: uuid.UUID,
        item_type: str,
        item_id: uuid.UUID,
        name_snapshot: str,
        price_snapshot: int,
        mrp_snapshot: int,
    ) -> BookingItem:
        item = BookingItem(
            booking_id=booking_id,
            patient_id=patient_id,
            item_type=item_type,
            item_id=item_id,
            name_snapshot=name_snapshot,
            price_snapshot=price_snapshot,
            mrp_snapshot=mrp_snapshot,
            status="PENDING",
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_status(
        self,
        *,
        booking: Booking,
        to_status: str,
        actor_user_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> None:
        from_status = booking.status
        booking.status = to_status
        booking.version += 1
        history = BookingStatusHistory(
            booking_id=booking.id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        self.session.add(history)
        await self.session.flush()
