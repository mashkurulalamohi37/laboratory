"""Business logic for sample handling and chain-of-custody."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.modules.sample.models import (
    Sample,
    SampleEvent,
    SampleRejectionReason,
    SampleStatus,
    SampleTransfer,
    SampleTransferItem,
    TransferStatus,
)
from app.modules.sample.repository import SampleRepository
from app.modules.sample.schemas import (
    SampleCollectRequest,
    SampleCreateRequest,
    SampleRejectRequest,
    TransferCreateRequest,
)


class SampleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SampleRepository(session)

    async def _generate_barcode(self) -> str:
        year = datetime.now(UTC).year
        count = await self._repo.count_samples_for_year(year)
        return f"SMP-{year}-{(count + 1):06d}"

    async def _generate_manifest_code(self) -> str:
        year = datetime.now(UTC).year
        count = await self._repo.count_transfers_for_year(year)
        return f"TRF-{year}-{(count + 1):06d}"

    async def create_sample(
        self, data: SampleCreateRequest, actor_id: uuid.UUID | None = None
    ) -> Sample:
        barcode = await self._generate_barcode()
        now = datetime.now(UTC)
        sample = Sample(
            barcode=barcode,
            booking_id=data.booking_id,
            booking_item_id=data.booking_item_id,
            patient_id=data.patient_id,
            sample_type_id=data.sample_type_id,
            container=data.container,
            status=SampleStatus.CREATED,
            collection_centre_id=data.collection_centre_id,
            lab_id=data.lab_id,
        )
        saved = await self._repo.save_sample(sample)

        event = SampleEvent(
            sample_id=saved.id,
            event_type="CREATED",
            location_type="CENTRE" if data.collection_centre_id else "HOME",
            location_id=data.collection_centre_id,
            actor_user_id=actor_id,
            notes="Sample record initialized and barcode generated",
            created_at=now,
        )
        await self._repo.add_event(event)
        return saved

    async def mark_collected(
        self,
        data: SampleCollectRequest,
        actor_id: uuid.UUID,
        location_type: str = "HOME",
        location_id: uuid.UUID | None = None,
    ) -> Sample:
        sample = await self._repo.get_by_id(data.sample_id)
        if not sample:
            raise NotFound(code="SAMPLE_NOT_FOUND", message="Sample not found")

        now = datetime.now(UTC)
        sample.status = SampleStatus.COLLECTED
        sample.collected_by = actor_id
        sample.collected_at = now
        if data.container:
            sample.container = data.container

        await self._repo.save_sample(sample)

        event = SampleEvent(
            sample_id=sample.id,
            event_type="COLLECTED",
            location_type=location_type,
            location_id=location_id,
            actor_user_id=actor_id,
            notes=f"Sample collected and labelled with barcode {sample.barcode}",
            created_at=now,
        )
        await self._repo.add_event(event)
        return sample

    async def receive_samples_at_lab(
        self, barcodes: list[str], lab_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[Sample]:
        received: list[Sample] = []
        now = datetime.now(UTC)
        for barcode in barcodes:
            sample = await self._repo.get_by_barcode(barcode.strip())
            if not sample:
                continue
            sample.status = SampleStatus.RECEIVED
            sample.lab_id = lab_id
            await self._repo.save_sample(sample)

            event = SampleEvent(
                sample_id=sample.id,
                event_type="RECEIVED_AT_LAB",
                location_type="LAB",
                location_id=lab_id,
                actor_user_id=actor_id,
                notes=f"Sample scanned and received at lab {lab_id}",
                created_at=now,
            )
            await self._repo.add_event(event)
            received.append(sample)
        return received

    async def reject_sample(
        self, sample_id: uuid.UUID, data: SampleRejectRequest, actor_id: uuid.UUID
    ) -> tuple[Sample, Sample | None]:
        sample = await self._repo.get_by_id(sample_id)
        if not sample:
            raise NotFound(code="SAMPLE_NOT_FOUND", message="Sample not found")

        reason = await self._repo.get_rejection_reason(data.rejection_reason_id)
        if not reason:
            raise NotFound(
                code="REASON_NOT_FOUND", message="Rejection reason not found"
            )

        now = datetime.now(UTC)
        sample.status = SampleStatus.REJECTED
        sample.rejection_reason_id = data.rejection_reason_id
        sample.rejection_notes = data.notes
        await self._repo.save_sample(sample)

        event = SampleEvent(
            sample_id=sample.id,
            event_type="REJECTED",
            location_type="LAB",
            location_id=sample.lab_id,
            actor_user_id=actor_id,
            notes=f"Sample rejected: {reason.name_en}. Notes: {data.notes or ''}",
            created_at=now,
        )
        await self._repo.add_event(event)

        recollection_sample: Sample | None = None
        if data.trigger_recollection and reason.requires_recollection:
            # Spawn recollection sample
            new_barcode = await self._generate_barcode()
            recollection_sample = Sample(
                barcode=new_barcode,
                booking_id=sample.booking_id,
                booking_item_id=sample.booking_item_id,
                patient_id=sample.patient_id,
                sample_type_id=sample.sample_type_id,
                container=sample.container,
                status=SampleStatus.CREATED,
                collection_centre_id=sample.collection_centre_id,
                lab_id=sample.lab_id,
                parent_sample_id=sample.id,
            )
            await self._repo.save_sample(recollection_sample)
            re_event = SampleEvent(
                sample_id=recollection_sample.id,
                event_type="RECOLLECTION_SPAWNED",
                location_type="LAB",
                location_id=sample.lab_id,
                actor_user_id=actor_id,
                notes=f"Recollection spawned from rejected sample {sample.barcode}",
                created_at=now,
            )
            await self._repo.add_event(re_event)

        return sample, recollection_sample

    async def create_transfer_manifest(
        self, data: TransferCreateRequest, actor_id: uuid.UUID
    ) -> SampleTransfer:
        manifest_code = await self._generate_manifest_code()
        now = datetime.now(UTC)
        transfer = SampleTransfer(
            manifest_code=manifest_code,
            source_centre_id=data.source_centre_id,
            destination_lab_id=data.destination_lab_id,
            status=TransferStatus.DISPATCHED,
            dispatched_by=actor_id,
            dispatched_at=now,
            temperature_celsius=data.temperature_celsius,
            sample_count=len(data.sample_ids),
        )
        saved_transfer = await self._repo.save_transfer(transfer)

        for sample_id in data.sample_ids:
            sample = await self._repo.get_by_id(sample_id)
            if sample:
                sample.status = SampleStatus.IN_TRANSIT
                await self._repo.save_sample(sample)

                item = SampleTransferItem(transfer_id=saved_transfer.id, sample_id=sample.id)
                self._session.add(item)

                event = SampleEvent(
                    sample_id=sample.id,
                    event_type="TRANSFERRED",
                    location_type="CENTRE",
                    location_id=data.source_centre_id,
                    actor_user_id=actor_id,
                    notes=f"Sample added to transfer manifest {manifest_code}",
                    created_at=now,
                )
                await self._repo.add_event(event)

        return saved_transfer

    async def receive_transfer(self, transfer_id: uuid.UUID, actor_id: uuid.UUID) -> SampleTransfer:
        transfer = await self._repo.get_transfer(transfer_id)
        if not transfer:
            raise NotFound(
                code="TRANSFER_NOT_FOUND", message="Transfer manifest not found"
            )

        now = datetime.now(UTC)
        transfer.status = TransferStatus.RECEIVED
        transfer.received_by = actor_id
        transfer.received_at = now
        await self._repo.save_transfer(transfer)

        for item in transfer.items:
            sample = item.sample
            if sample:
                sample.status = SampleStatus.RECEIVED
                sample.lab_id = transfer.destination_lab_id
                await self._repo.save_sample(sample)

                event = SampleEvent(
                    sample_id=sample.id,
                    event_type="RECEIVED_AT_LAB",
                    location_type="LAB",
                    location_id=transfer.destination_lab_id,
                    actor_user_id=actor_id,
                    notes=f"Sample received at lab via transfer {transfer.manifest_code}",
                    created_at=now,
                )
                await self._repo.add_event(event)

        return transfer

    async def get_by_barcode(self, barcode: str) -> Sample | None:
        return await self._repo.get_by_barcode(barcode)

    async def get_by_id(self, sample_id: uuid.UUID) -> Sample | None:
        return await self._repo.get_by_id(sample_id)

    async def list_by_booking(self, booking_id: uuid.UUID) -> Sequence[Sample]:
        return await self._repo.list_by_booking(booking_id)

    async def list_rejection_reasons(self) -> Sequence[SampleRejectionReason]:
        return await self._repo.list_rejection_reasons()

    async def list_transfers(
        self, destination_lab_id: uuid.UUID | None = None, status: str | None = None
    ) -> Sequence[SampleTransfer]:
        return await self._repo.list_transfers(destination_lab_id, status)
