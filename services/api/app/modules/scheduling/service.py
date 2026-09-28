"""Service for slot scheduling, capacity checks, and hold management."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.modules.scheduling.models import SlotInstance
from app.modules.scheduling.repository import SchedulingRepository
from app.modules.scheduling.schemas import SlotHoldResponse, SlotInstanceResponse


class SchedulingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SchedulingRepository(session)

    async def get_available_slots(
        self,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
        from_date: dt.date,
        to_date: dt.date,
        mode: str,
    ) -> list[SlotInstanceResponse]:
        # Release any expired holds first
        await self.repo.release_expired_holds(dt.datetime.now(dt.UTC))

        # Check if slots exist for the date range; if not, materialize default slots
        slots = await self.repo.get_slots_by_date_range(
            owner_type=owner_type,
            owner_id=owner_id,
            from_date=from_date,
            to_date=to_date,
            mode=mode,
        )

        if not slots:
            # Auto-materialize default standard slots (e.g. 08:00 to 18:00 every 2 hours) if empty
            await self._generate_default_slots_for_range(
                owner_type=owner_type,
                owner_id=owner_id,
                from_date=from_date,
                to_date=to_date,
                mode=mode,
            )
            slots = await self.repo.get_slots_by_date_range(
                owner_type=owner_type,
                owner_id=owner_id,
                from_date=from_date,
                to_date=to_date,
                mode=mode,
            )

        result: list[SlotInstanceResponse] = []
        for s in slots:
            available = max(0, s.capacity - (s.booked + s.held))
            res = SlotInstanceResponse(
                id=s.id,
                owner_type=s.owner_type,
                owner_id=s.owner_id,
                date=s.date,
                start_time=s.start_time,
                end_time=s.end_time,
                capacity=s.capacity,
                booked=s.booked,
                held=s.held,
                mode=s.mode,
                is_active=s.is_active,
                available=available,
            )
            result.append(res)
        return result

    async def _generate_default_slots_for_range(
        self,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
        from_date: dt.date,
        to_date: dt.date,
        mode: str,
    ) -> None:
        standard_windows = [
            (dt.time(8, 0), dt.time(10, 0)),
            (dt.time(10, 0), dt.time(12, 0)),
            (dt.time(12, 0), dt.time(14, 0)),
            (dt.time(14, 0), dt.time(16, 0)),
            (dt.time(16, 0), dt.time(18, 0)),
            (dt.time(18, 0), dt.time(20, 0)),
        ]
        curr = from_date
        while curr <= to_date:
            for start, end in standard_windows:
                instance = SlotInstance(
                    owner_type=owner_type,
                    owner_id=owner_id,
                    date=curr,
                    start_time=start,
                    end_time=end,
                    capacity=10,
                    booked=0,
                    held=0,
                    mode=mode,
                    is_active=True,
                )
                self.session.add(instance)
            curr += dt.timedelta(days=1)
        await self.session.flush()

    async def hold_slot(
        self,
        *,
        slot_id: uuid.UUID,
        user_id: uuid.UUID,
        ttl_minutes: int = 10,
    ) -> SlotHoldResponse:
        slot = await self.repo.get_slot_for_update(slot_id)
        if not slot:
            raise NotFound("Slot not found")

        available = slot.capacity - (slot.booked + slot.held)
        if available <= 0:
            raise Conflict("Selected slot is fully booked")

        expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=ttl_minutes)
        slot.held += 1
        hold = await self.repo.create_hold(
            slot_id=slot_id,
            user_id=user_id,
            expires_at=expires_at,
        )
        return SlotHoldResponse(
            hold_id=hold.id,
            slot_id=slot.id,
            expires_at=expires_at,
            message="Slot held successfully for checkout",
        )
