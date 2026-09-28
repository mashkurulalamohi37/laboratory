"""FastAPI router for slot scheduling and holds."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal
from app.modules.scheduling.schemas import (
    SlotHoldRequest,
    SlotHoldResponse,
    SlotInstanceResponse,
)
from app.modules.scheduling.service import SchedulingService

router = APIRouter(tags=["scheduling"])


def get_scheduling_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SchedulingService:
    return SchedulingService(session)


@router.get("/slots/available", response_model=Envelope[list[SlotInstanceResponse]])
async def get_available_slots(
    owner_type: Annotated[str, Query(description="CENTRE or ZONE")],
    owner_id: Annotated[uuid.UUID, Query(description="Centre ID or Zone ID")],
    from_date: Annotated[dt.date, Query(description="Start date")],
    to_date: Annotated[dt.date, Query(description="End date")],
    mode: Annotated[str, Query(description="HOME or CENTRE")] = "CENTRE",
    service: Annotated[SchedulingService, Depends(get_scheduling_service)] = None,  # type: ignore[assignment]
) -> Envelope[list[SlotInstanceResponse]]:
    slots = await service.get_available_slots(
        owner_type=owner_type,
        owner_id=owner_id,
        from_date=from_date,
        to_date=to_date,
        mode=mode,
    )
    return ok(slots)


@router.post("/slots/hold", response_model=Envelope[SlotHoldResponse])
async def hold_slot(
    body: SlotHoldRequest,
    principal: CurrentPrincipal,
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
) -> Envelope[SlotHoldResponse]:
    res = await service.hold_slot(
        slot_id=body.slot_id,
        user_id=principal.user_id,
        ttl_minutes=body.ttl_minutes,
    )
    return ok(res)
