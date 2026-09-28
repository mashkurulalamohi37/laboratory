"""API routes for the lab module."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.lab.schemas import LabOrderCreate, LabOrderItemOut, LabOrderOut
from app.modules.lab.service import LabService

router = APIRouter(prefix="/lab", tags=["Lab"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> LabService:
    return LabService(session)


@router.post("/orders", response_model=Envelope[LabOrderOut])
async def create_order(
    data: LabOrderCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.LAB_VIEW))],
    service: Annotated[LabService, Depends(get_service)],
) -> Envelope[LabOrderOut]:
    item = await service.create_order(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/orders/{order_id}", response_model=Envelope[LabOrderOut | None])
async def get_order(
    order_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.LAB_VIEW))],
    service: Annotated[LabService, Depends(get_service)],
) -> Envelope[LabOrderOut | None]:
    item = await service.get_order_by_id(order_id)
    return ok(item)  # type: ignore[arg-type]


@router.get("/orders/by-booking/{booking_id}", response_model=Envelope[LabOrderOut | None])
async def get_order_by_booking(
    booking_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.LAB_VIEW))],
    service: Annotated[LabService, Depends(get_service)],
) -> Envelope[LabOrderOut | None]:
    item = await service.get_order_by_booking(booking_id)
    return ok(item)  # type: ignore[arg-type]


@router.get("/worklist", response_model=Envelope[list[LabOrderItemOut]])
async def list_worklist(
    _: Annotated[CurrentPrincipal, Depends(require(P.LAB_VIEW))],
    service: Annotated[LabService, Depends(get_service)],
    department_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    lab_id: uuid.UUID | None = Query(None),
) -> Envelope[list[LabOrderItemOut]]:
    items = await service.list_worklist(department_id, status, lab_id)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/items/{item_id}/link-sample/{sample_id}", response_model=Envelope[LabOrderItemOut])
async def link_sample(
    item_id: uuid.UUID,
    sample_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.SAMPLE_RECEIVE))],
    service: Annotated[LabService, Depends(get_service)],
) -> Envelope[LabOrderItemOut]:
    item = await service.link_sample_to_item(item_id, sample_id)
    return ok(item)  # type: ignore[arg-type]
