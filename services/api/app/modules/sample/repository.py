"""Database repository for sample operations."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.sample.models import (
    Sample,
    SampleEvent,
    SampleRejectionReason,
    SampleTransfer,
    SampleTransferItem,
)


class SampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_barcode(self, barcode: str) -> Sample | None:
        stmt = select(Sample).options(selectinload(Sample.events)).where(Sample.barcode == barcode)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, sample_id: uuid.UUID) -> Sample | None:
        stmt = select(Sample).options(selectinload(Sample.events)).where(Sample.id == sample_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_booking(self, booking_id: uuid.UUID) -> Sequence[Sample]:
        stmt = (
            select(Sample)
            .options(selectinload(Sample.events))
            .where(Sample.booking_id == booking_id)
            .order_by(Sample.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_samples_for_year(self, year: int) -> int:
        stmt = select(func.count(Sample.id))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def count_transfers_for_year(self, year: int) -> int:
        stmt = select(func.count(SampleTransfer.id))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def save_sample(self, sample: Sample) -> Sample:
        self._session.add(sample)
        await self._session.flush()
        return sample

    async def add_event(self, event: SampleEvent) -> SampleEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_rejection_reasons(self) -> Sequence[SampleRejectionReason]:
        stmt = select(SampleRejectionReason).where(SampleRejectionReason.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_rejection_reason(self, reason_id: uuid.UUID) -> SampleRejectionReason | None:
        stmt = select(SampleRejectionReason).where(SampleRejectionReason.id == reason_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_transfer(self, transfer: SampleTransfer) -> SampleTransfer:
        self._session.add(transfer)
        await self._session.flush()
        return transfer

    async def get_transfer(self, transfer_id: uuid.UUID) -> SampleTransfer | None:
        stmt = (
            select(SampleTransfer)
            .options(selectinload(SampleTransfer.items).selectinload(SampleTransferItem.sample))
            .where(SampleTransfer.id == transfer_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_transfers(
        self, destination_lab_id: uuid.UUID | None = None, status: str | None = None
    ) -> Sequence[SampleTransfer]:
        stmt = select(SampleTransfer).order_by(SampleTransfer.created_at.desc())
        if destination_lab_id:
            stmt = stmt.where(SampleTransfer.destination_lab_id == destination_lab_id)
        if status:
            stmt = stmt.where(SampleTransfer.status == status)
        result = await self._session.execute(stmt)
        return result.scalars().all()
