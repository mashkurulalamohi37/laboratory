"""Repository for slot templates, instances, and concurrency-safe holds."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduling.models import SlotHold, SlotInstance, SlotTemplate


class SchedulingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_templates_for_owner(
        self, owner_type: str, owner_id: uuid.UUID
    ) -> Sequence[SlotTemplate]:
        query = select(SlotTemplate).where(
            SlotTemplate.owner_type == owner_type,
            SlotTemplate.owner_id == owner_id,
            SlotTemplate.is_active.is_(True),
        )
        return (await self.session.execute(query)).scalars().all()

    async def get_slots_by_date_range(
        self,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
        from_date: dt.date,
        to_date: dt.date,
        mode: str,
    ) -> Sequence[SlotInstance]:
        query = (
            select(SlotInstance)
            .where(
                SlotInstance.owner_type == owner_type,
                SlotInstance.owner_id == owner_id,
                SlotInstance.date >= from_date,
                SlotInstance.date <= to_date,
                SlotInstance.mode == mode,
                SlotInstance.is_active.is_(True),
            )
            .order_by(SlotInstance.date.asc(), SlotInstance.start_time.asc())
        )
        return (await self.session.execute(query)).scalars().all()

    async def get_slot_for_update(self, slot_id: uuid.UUID) -> SlotInstance | None:
        """Lock the row using SELECT ... FOR UPDATE for concurrency safety."""
        query = select(SlotInstance).where(SlotInstance.id == slot_id).with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_slot_by_id(self, slot_id: uuid.UUID) -> SlotInstance | None:
        query = select(SlotInstance).where(SlotInstance.id == slot_id)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_hold(
        self,
        *,
        slot_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_at: dt.datetime,
        booking_id: uuid.UUID | None = None,
    ) -> SlotHold:
        hold = SlotHold(
            slot_id=slot_id,
            user_id=user_id,
            expires_at=expires_at,
            booking_id=booking_id,
        )
        self.session.add(hold)
        await self.session.flush()
        return hold

    async def release_expired_holds(self, now: dt.datetime) -> int:
        """Find expired holds and reduce held count on slot instances."""
        query = (
            select(SlotHold)
            .where(SlotHold.expires_at <= now, SlotHold.booking_id.is_(None))
            .with_for_update()
        )
        expired_holds = (await self.session.execute(query)).scalars().all()
        if not expired_holds:
            return 0

        count = len(expired_holds)
        for hold in expired_holds:
            slot = await self.get_slot_for_update(hold.slot_id)
            if slot and slot.held > 0:
                slot.held -= 1
            await self.session.delete(hold)

        await self.session.flush()
        return count
