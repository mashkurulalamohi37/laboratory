"""API routes for sample handling and tracking."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.sample.schemas import (
    SampleCollectRequest,
    SampleCreateRequest,
    SampleOut,
    SampleReceiveRequest,
    SampleRejectionReasonOut,
    SampleRejectRequest,
    TransferCreateRequest,
    TransferOut,
)
from app.modules.sample.service import SampleService

router = APIRouter(prefix="/samples", tags=["Samples"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> SampleService:
    return SampleService(session)


@router.get("/rejection-reasons", response_model=Envelope[list[SampleRejectionReasonOut]])
async def list_rejection_reasons(
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[list[SampleRejectionReasonOut]]:
    items = await service.list_rejection_reasons()
    return ok(list(items))  # type: ignore[arg-type]


@router.post("", response_model=Envelope[SampleOut])
async def create_sample(
    data: SampleCreateRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_VIEW))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[SampleOut]:
    item = await service.create_sample(data, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


@router.get("/barcode/{barcode}", response_model=Envelope[SampleOut | None])
async def get_by_barcode(
    barcode: str,
    _: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_VIEW))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[SampleOut | None]:
    item = await service.get_by_barcode(barcode)
    return ok(item)  # type: ignore[arg-type]


@router.get("/booking/{booking_id}", response_model=Envelope[list[SampleOut]])
async def list_booking_samples(
    booking_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_VIEW))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[list[SampleOut]]:
    items = await service.list_by_booking(booking_id)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/collect", response_model=Envelope[SampleOut])
async def mark_collected(
    data: SampleCollectRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_PERFORM))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[SampleOut]:
    item = await service.mark_collected(data, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


@router.post("/receive", response_model=Envelope[list[SampleOut]])
async def receive_samples(
    data: SampleReceiveRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_RECEIVE))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[list[SampleOut]]:
    items = await service.receive_samples_at_lab(
        data.barcodes, data.lab_id, actor_id=principal.user_id
    )
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/{sample_id}/reject", response_model=Envelope[SampleOut])
async def reject_sample(
    sample_id: uuid.UUID,
    data: SampleRejectRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_REJECT))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[SampleOut]:
    sample, _ = await service.reject_sample(sample_id, data, actor_id=principal.user_id)
    return ok(sample)  # type: ignore[arg-type]


@router.post("/transfers", response_model=Envelope[TransferOut])
async def create_transfer(
    data: TransferCreateRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_TRANSFER))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[TransferOut]:
    item = await service.create_transfer_manifest(data, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


@router.get("/transfers", response_model=Envelope[list[TransferOut]])
async def list_transfers(
    _: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_VIEW))],
    service: Annotated[SampleService, Depends(get_service)],
    destination_lab_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
) -> Envelope[list[TransferOut]]:
    items = await service.list_transfers(destination_lab_id, status)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/transfers/{transfer_id}/receive", response_model=Envelope[TransferOut])
async def receive_transfer(
    transfer_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_RECEIVE))],
    service: Annotated[SampleService, Depends(get_service)],
) -> Envelope[TransferOut]:
    item = await service.receive_transfer(transfer_id, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]
