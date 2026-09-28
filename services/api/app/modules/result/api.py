"""API routes for result entry, verification and critical alerts."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.result.schemas import (
    AlertAcknowledgeRequest,
    CriticalAlertOut,
    ResultAmendRequest,
    ResultEnterRequest,
    ResultOut,
    ResultReturnRequest,
    ResultVerifyRequest,
)
from app.modules.result.service import ResultService

router = APIRouter(prefix="/results", tags=["Results"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ResultService:
    return ResultService(session)


@router.post("/enter", response_model=Envelope[ResultOut])
async def enter_results(
    data: ResultEnterRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.RESULT_ENTER))],
    service: Annotated[ResultService, Depends(get_service)],
) -> Envelope[ResultOut]:
    """Enter parameter values (numeric/text). Flags (L, H, CL, CH) are auto-computed."""
    item = await service.enter_results(data, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


@router.get("/for-item/{lab_order_item_id}", response_model=Envelope[ResultOut | None])
async def get_current_result(
    lab_order_item_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.RESULT_VIEW))],
    service: Annotated[ResultService, Depends(get_service)],
) -> Envelope[ResultOut | None]:
    item = await service.get_current_result(lab_order_item_id)
    return ok(item)  # type: ignore[arg-type]


@router.post("/{result_id}/verify", response_model=Envelope[ResultOut])
async def verify_result(
    result_id: uuid.UUID,
    data: ResultVerifyRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.RESULT_VERIFY))],
    service: Annotated[ResultService, Depends(get_service)],
) -> Envelope[ResultOut]:
    """Pathologist verification of results with four-eyes enforcement."""
    item = await service.verify_result(
        result_id, data, actor_id=principal.user_id
    )
    return ok(item)  # type: ignore[arg-type]


@router.post("/{result_id}/return", response_model=Envelope[ResultOut])
async def return_result(
    result_id: uuid.UUID,
    data: ResultReturnRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.RESULT_VERIFY))],
    service: Annotated[ResultService, Depends(get_service)],
) -> Envelope[ResultOut]:
    """Return result back to lab technician with reason for re-testing or review."""
    item = await service.return_result(
        result_id, data, actor_id=principal.user_id
    )
    return ok(item)  # type: ignore[arg-type]


@router.post("/{result_id}/amend", response_model=Envelope[ResultOut])
async def amend_result(
    result_id: uuid.UUID,
    data: ResultAmendRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.RESULT_EDIT))],
    service: Annotated[ResultService, Depends(get_service)],
) -> Envelope[ResultOut]:
    """Amend a previously verified result with mandatory reason (creates version n+1)."""
    item = await service.amend_result(
        result_id, data, actor_id=principal.user_id
    )
    return ok(item)  # type: ignore[arg-type]


@router.get("/critical-alerts", response_model=Envelope[list[CriticalAlertOut]])
async def list_critical_alerts(
    _: Annotated[CurrentPrincipal, Depends(require(P.RESULT_VIEW))],
    service: Annotated[ResultService, Depends(get_service)],
    status: str | None = Query(None),
) -> Envelope[list[CriticalAlertOut]]:
    """List critical laboratory value alerts."""
    items = await service.list_critical_alerts(status)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/critical-alerts/{alert_id}/acknowledge", response_model=Envelope[CriticalAlertOut])
async def acknowledge_alert(
    alert_id: uuid.UUID,
    data: AlertAcknowledgeRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.RESULT_VIEW))],
    service: Annotated[ResultService, Depends(get_service)],
) -> Envelope[CriticalAlertOut]:
    item = await service.acknowledge_alert(
        alert_id, data, actor_id=principal.user_id
    )
    return ok(item)  # type: ignore[arg-type]
