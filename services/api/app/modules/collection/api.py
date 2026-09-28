"""API routes for the collection module."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.collection.schemas import (
    AssignmentStatusUpdate,
    CollectionAssignmentOut,
    CollectorCreate,
    CollectorOut,
    ManualAssignRequest,
)
from app.modules.collection.service import CollectionService

router = APIRouter(prefix="/collection", tags=["Collection"])
admin_router = APIRouter(prefix="/admin/collection", tags=["Collection Admin"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CollectionService:
    return CollectionService(session)


@router.get("/me/assignments", response_model=Envelope[list[CollectionAssignmentOut]])
async def list_my_assignments(
    principal: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_PERFORM))],
    service: Annotated[CollectionService, Depends(get_service)],
    target_date: date | None = Query(None),
) -> Envelope[list[CollectionAssignmentOut]]:
    """Collector view: List assigned pickups for today/date."""
    items = await service.list_collector_assignments(principal.user_id, target_date)
    return ok(list(items))  # type: ignore[arg-type]


@router.post(
    "/assignments/{assignment_id}/status", response_model=Envelope[CollectionAssignmentOut]
)
async def update_assignment_status(
    assignment_id: uuid.UUID,
    data: AssignmentStatusUpdate,
    principal: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_PERFORM))],
    service: Annotated[CollectionService, Depends(get_service)],
) -> Envelope[CollectionAssignmentOut]:
    """Transition assignment state (e.g. ACCEPTED -> ARRIVED -> COLLECTED)."""
    item = await service.update_status(assignment_id, data, actor_user_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


# Admin routes
@admin_router.post("/collectors", response_model=Envelope[CollectorOut])
async def register_collector(
    data: CollectorCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_ASSIGN))],
    service: Annotated[CollectionService, Depends(get_service)],
) -> Envelope[CollectorOut]:
    item = await service.register_collector(data)
    return ok(item)  # type: ignore[arg-type]


@admin_router.get("/collectors", response_model=Envelope[list[CollectorOut]])
async def list_collectors(
    _: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_VIEW))],
    service: Annotated[CollectionService, Depends(get_service)],
    branch_id: uuid.UUID | None = Query(None),
) -> Envelope[list[CollectorOut]]:
    items = await service.list_active_collectors(branch_id)
    return ok(list(items))  # type: ignore[arg-type]


@admin_router.get("/assignments", response_model=Envelope[list[CollectionAssignmentOut]])
async def list_admin_assignments(
    _: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_VIEW))],
    service: Annotated[CollectionService, Depends(get_service)],
    target_date: date | None = Query(None),
    status: str | None = Query(None),
    collector_id: uuid.UUID | None = Query(None),
) -> Envelope[list[CollectionAssignmentOut]]:
    items = await service.list_all_assignments(target_date, status, collector_id)
    return ok(list(items))  # type: ignore[arg-type]


@admin_router.post("/assignments/assign", response_model=Envelope[CollectionAssignmentOut])
async def assign_manually(
    data: ManualAssignRequest,
    _: Annotated[CurrentPrincipal, Depends(require(P.COLLECTION_ASSIGN))],
    service: Annotated[CollectionService, Depends(get_service)],
) -> Envelope[CollectionAssignmentOut]:
    item = await service.assign_manually(data)
    return ok(item)  # type: ignore[arg-type]
