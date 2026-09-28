"""Business logic for collection domain."""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict, NotFound
from app.modules.collection.models import (
    AssignmentStatus,
    CollectionAssignment,
    CollectionEvent,
    Collector,
)
from app.modules.collection.repository import CollectionRepository
from app.modules.collection.schemas import (
    AssignmentStatusUpdate,
    CollectorCreate,
    ManualAssignRequest,
)


class CollectionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CollectionRepository(session)

    async def register_collector(self, data: CollectorCreate) -> Collector:
        existing = await self._repo.get_collector_by_user(data.user_id)
        if existing:
            raise Conflict(
                code="COLLECTOR_EXISTS",
                message="User is already registered as a collector",
            )

        collector = Collector(
            user_id=data.user_id,
            branch_id=data.branch_id,
            phone=data.phone,
            daily_capacity=data.daily_capacity,
            vehicle_type=data.vehicle_type,
            is_active=True,
        )
        return await self._repo.create_collector(collector)

    async def get_collector_by_user(self, user_id: uuid.UUID) -> Collector | None:
        return await self._repo.get_collector_by_user(user_id)

    async def list_active_collectors(
        self, branch_id: uuid.UUID | None = None
    ) -> Sequence[Collector]:
        return await self._repo.list_active_collectors(branch_id)

    async def get_or_create_assignment(
        self, booking_id: uuid.UUID, scheduled_date: date, slot_id: uuid.UUID | None = None
    ) -> CollectionAssignment:
        existing = await self._repo.get_assignment_by_booking(booking_id)
        if existing:
            return existing

        # Generate 4-digit verification code
        code = f"{secrets.randbelow(9000) + 1000}"
        assignment = CollectionAssignment(
            booking_id=booking_id,
            scheduled_date=scheduled_date,
            slot_id=slot_id,
            status=AssignmentStatus.PENDING,
            verification_code=code,
        )
        return await self._repo.save_assignment(assignment)

    async def assign_manually(self, data: ManualAssignRequest) -> CollectionAssignment:
        collector = await self._repo.get_collector(data.collector_id)
        if not collector or not collector.is_active:
            raise NotFound(
                code="COLLECTOR_NOT_FOUND",
                message="Collector not found or inactive",
            )

        assignment = await self._repo.get_assignment_by_booking(data.booking_id)
        if not assignment:
            code = f"{secrets.randbelow(9000) + 1000}"
            assignment = CollectionAssignment(
                booking_id=data.booking_id,
                collector_id=data.collector_id,
                status=AssignmentStatus.ASSIGNED,
                scheduled_date=data.scheduled_date,
                slot_id=data.slot_id,
                verification_code=code,
                notes=data.notes,
            )
        else:
            assignment.collector_id = data.collector_id
            assignment.status = AssignmentStatus.ASSIGNED
            assignment.scheduled_date = data.scheduled_date
            if data.slot_id:
                assignment.slot_id = data.slot_id
            if data.notes:
                assignment.notes = data.notes

        return await self._repo.save_assignment(assignment)

    async def update_status(
        self, assignment_id: uuid.UUID, data: AssignmentStatusUpdate, actor_user_id: uuid.UUID
    ) -> CollectionAssignment:
        assignment = await self._repo.get_assignment(assignment_id)
        if not assignment:
            raise NotFound(
                code="ASSIGNMENT_NOT_FOUND", message="Assignment not found"
            )

        now = datetime.now(UTC)
        target_status = data.status.upper()

        if target_status == AssignmentStatus.PATIENT_VERIFIED:
            if not data.verification_code or data.verification_code != assignment.verification_code:
                raise AppError(
                    code="INVALID_VERIFICATION_CODE",
                    message="Patient verification code is invalid",
                )
            assignment.patient_verified_at = now

        elif target_status == AssignmentStatus.ACCEPTED:
            assignment.accepted_at = now
        elif target_status == AssignmentStatus.ARRIVED:
            assignment.arrived_at = now
        elif target_status == AssignmentStatus.COLLECTED:
            if not assignment.patient_verified_at:
                raise AppError(
                    code="PATIENT_NOT_VERIFIED",
                    message="Patient must be verified before marking collection complete",
                )
            assignment.collected_at = now

        assignment.status = target_status
        if data.notes:
            assignment.notes = data.notes

        await self._repo.save_assignment(assignment)

        # Record event for audit / offline queue trace
        event = CollectionEvent(
            assignment_id=assignment.id,
            status=target_status,
            lat=data.lat,
            lng=data.lng,
            actor_user_id=actor_user_id,
            client_timestamp=data.client_timestamp or now,
            notes=data.notes,
        )
        await self._repo.add_event(event)

        return assignment

    async def list_collector_assignments(
        self, user_id: uuid.UUID, target_date: date | None = None
    ) -> Sequence[CollectionAssignment]:
        collector = await self._repo.get_collector_by_user(user_id)
        if not collector:
            return []
        return await self._repo.list_collector_assignments(collector.id, target_date)

    async def list_all_assignments(
        self,
        target_date: date | None = None,
        status: str | None = None,
        collector_id: uuid.UUID | None = None,
    ) -> Sequence[CollectionAssignment]:
        return await self._repo.list_all_assignments(target_date, status, collector_id)
