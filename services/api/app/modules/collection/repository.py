"""Database repository for collection domain."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.collection.models import CollectionAssignment, CollectionEvent, Collector


class CollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_collector_by_user(self, user_id: uuid.UUID) -> Collector | None:
        stmt = select(Collector).where(Collector.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_collector(self, collector_id: uuid.UUID) -> Collector | None:
        stmt = select(Collector).where(Collector.id == collector_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_collectors(
        self, branch_id: uuid.UUID | None = None
    ) -> Sequence[Collector]:
        stmt = select(Collector).where(Collector.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Collector.branch_id == branch_id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create_collector(self, collector: Collector) -> Collector:
        self._session.add(collector)
        await self._session.flush()
        return collector

    async def get_assignment(self, assignment_id: uuid.UUID) -> CollectionAssignment | None:
        stmt = (
            select(CollectionAssignment)
            .options(selectinload(CollectionAssignment.events))
            .where(CollectionAssignment.id == assignment_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignment_by_booking(self, booking_id: uuid.UUID) -> CollectionAssignment | None:
        stmt = (
            select(CollectionAssignment)
            .options(selectinload(CollectionAssignment.events))
            .where(CollectionAssignment.id == booking_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_collector_assignments(
        self, collector_id: uuid.UUID, target_date: date | None = None
    ) -> Sequence[CollectionAssignment]:
        stmt = (
            select(CollectionAssignment)
            .options(selectinload(CollectionAssignment.events))
            .where(CollectionAssignment.collector_id == collector_id)
        )
        if target_date:
            stmt = stmt.where(CollectionAssignment.scheduled_date == target_date)
        stmt = stmt.order_by(CollectionAssignment.created_at.asc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_all_assignments(
        self,
        target_date: date | None = None,
        status: str | None = None,
        collector_id: uuid.UUID | None = None,
    ) -> Sequence[CollectionAssignment]:
        stmt = select(CollectionAssignment).options(selectinload(CollectionAssignment.events))
        if target_date:
            stmt = stmt.where(CollectionAssignment.scheduled_date == target_date)
        if status:
            stmt = stmt.where(CollectionAssignment.status == status)
        if collector_id:
            stmt = stmt.where(CollectionAssignment.collector_id == collector_id)
        stmt = stmt.order_by(
            CollectionAssignment.scheduled_date.asc(), CollectionAssignment.created_at.asc()
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_collector_assignments_for_date(
        self, collector_id: uuid.UUID, target_date: date
    ) -> int:
        stmt = (
            select(func.count(CollectionAssignment.id))
            .where(CollectionAssignment.collector_id == collector_id)
            .where(CollectionAssignment.scheduled_date == target_date)
            .where(CollectionAssignment.status.notin_(["CANCELLED"]))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def save_assignment(self, assignment: CollectionAssignment) -> CollectionAssignment:
        self._session.add(assignment)
        await self._session.flush()
        return assignment

    async def add_event(self, event: CollectionEvent) -> CollectionEvent:
        self._session.add(event)
        await self._session.flush()
        return event
