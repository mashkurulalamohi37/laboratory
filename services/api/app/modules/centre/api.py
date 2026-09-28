"""Centre locator (public) and branch/lab/centre/holiday administration (console)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.http import IfMatch, public_cache
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import require
from app.modules.auth.permissions import P
from app.modules.auth.principal import Principal
from app.modules.centre.schemas import (
    AdminCentreOut,
    AdminHolidayOut,
    BranchIn,
    BranchOut,
    BranchUpdate,
    CentreDetail,
    CentreIn,
    CentreService,
    CentreSummary,
    CentreUpdate,
    HolidayIn,
    LabIn,
    LabOut,
    LabUpdate,
)
from app.modules.centre.service import CentreAdminService, CentreFilters
from app.modules.centre.service import CentreService as Centres

router = APIRouter(prefix="/centres", tags=["public: centres"])
admin_router = APIRouter(prefix="/admin", tags=["admin: centres"])

Db = Annotated[AsyncSession, Depends(get_session)]
Manager = Annotated[Principal, Depends(require(P.CENTRE_MANAGE))]
#: Branch/lab/centre lists are needed by catalog and pricing screens as well.
Viewer = Annotated[
    Principal, Depends(require(P.CENTRE_MANAGE, P.TEST_VIEW, P.PRICE_MANAGE, any_of=True))
]
_ERR = error_responses(400, 401, 403, 404, 409, 422)


def _admin(db: AsyncSession, actor: Principal) -> CentreAdminService:
    return CentreAdminService(db, actor.user_id, actor.role_codes)


# ---------------------------------------------------------------- public
@router.get(
    "",
    summary="Find centres",
    description="Filter by location, service, open-now, or distance from a point "
    "(`lat`,`lng`, optional `radius_km`; results are then sorted by distance).",
    responses=error_responses(400),
)
async def list_centres(
    db: Db,
    response: Response,
    q: Annotated[str | None, Query(max_length=80)] = None,
    district_id: uuid.UUID | None = None,
    upazila_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    service: CentreService | None = None,
    open_now: bool = False,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=500)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[list[CentreSummary]]:
    # Open-now depends on the clock, so shared caches keep it only briefly.
    public_cache(response, 30)
    filters = CentreFilters(
        q=q,
        district_id=district_id,
        upazila_id=upazila_id,
        area_id=area_id,
        service=service,
        open_now=open_now,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )
    items, total = await Centres(db).list_centres(filters, page=page, page_size=page_size)
    return ok(items, page=page, page_size=page_size, total=total)


@router.get("/{slug}", summary="Centre details", responses=error_responses(404))
async def get_centre(slug: str, db: Db, response: Response) -> Envelope[CentreDetail]:
    public_cache(response, 30)
    return ok(await Centres(db).get_centre(slug))


# ---------------------------------------------------------------- admin: branches & labs
@admin_router.get("/branches", summary="List branches", responses=_ERR)
async def list_branches(actor: Viewer, db: Db) -> Envelope[list[BranchOut]]:
    return ok(await _admin(db, actor).list_branches())


@admin_router.post(
    "/branches", status_code=status.HTTP_201_CREATED, summary="Create a branch", responses=_ERR
)
async def create_branch(body: BranchIn, actor: Manager, db: Db) -> Envelope[BranchOut]:
    return ok(await _admin(db, actor).create_branch(body))


@admin_router.patch("/branches/{branch_id}", summary="Update a branch", responses=_ERR)
async def update_branch(
    branch_id: uuid.UUID, body: BranchUpdate, actor: Manager, db: Db, if_match: IfMatch
) -> Envelope[BranchOut]:
    return ok(await _admin(db, actor).update_branch(branch_id, body, if_match))


@admin_router.get("/labs", summary="List labs", responses=_ERR)
async def list_labs(actor: Viewer, db: Db) -> Envelope[list[LabOut]]:
    return ok(await _admin(db, actor).list_labs())


@admin_router.post(
    "/labs", status_code=status.HTTP_201_CREATED, summary="Create a lab", responses=_ERR
)
async def create_lab(body: LabIn, actor: Manager, db: Db) -> Envelope[LabOut]:
    return ok(await _admin(db, actor).create_lab(body))


@admin_router.patch("/labs/{lab_id}", summary="Update a lab", responses=_ERR)
async def update_lab(
    lab_id: uuid.UUID, body: LabUpdate, actor: Manager, db: Db, if_match: IfMatch
) -> Envelope[LabOut]:
    return ok(await _admin(db, actor).update_lab(lab_id, body, if_match))


# ---------------------------------------------------------------- admin: centres
@admin_router.get("/centres", summary="List centres (console)", responses=_ERR)
async def admin_list_centres(
    actor: Viewer,
    db: Db,
    q: Annotated[str | None, Query(max_length=80)] = None,
    branch_id: uuid.UUID | None = None,
    include_inactive: bool = True,
) -> Envelope[list[AdminCentreOut]]:
    return ok(
        await _admin(db, actor).list_centres(
            q=q, branch_id=branch_id, include_inactive=include_inactive
        )
    )


@admin_router.post(
    "/centres", status_code=status.HTTP_201_CREATED, summary="Create a centre", responses=_ERR
)
async def create_centre(body: CentreIn, actor: Manager, db: Db) -> Envelope[AdminCentreOut]:
    return ok(await _admin(db, actor).create_centre(body))


@admin_router.get("/centres/{centre_id}", summary="Get a centre (console)", responses=_ERR)
async def admin_get_centre(centre_id: uuid.UUID, actor: Viewer, db: Db) -> Envelope[AdminCentreOut]:
    return ok(await _admin(db, actor).get_centre(centre_id))


@admin_router.patch(
    "/centres/{centre_id}",
    summary="Update a centre",
    description="Partial update. `hours`, when present, replaces the whole week.",
    responses=_ERR,
)
async def update_centre(
    centre_id: uuid.UUID, body: CentreUpdate, actor: Manager, db: Db, if_match: IfMatch
) -> Envelope[AdminCentreOut]:
    return ok(await _admin(db, actor).update_centre(centre_id, body, if_match))


@admin_router.delete(
    "/centres/{centre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a centre (soft)",
    responses=_ERR,
)
async def delete_centre(
    centre_id: uuid.UUID, actor: Manager, db: Db, if_match: IfMatch
) -> Response:
    await _admin(db, actor).delete_centre(centre_id, if_match)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- admin: holidays
@admin_router.get("/holidays", summary="List branch holidays", responses=_ERR)
async def list_holidays(
    actor: Viewer,
    db: Db,
    branch_id: uuid.UUID | None = None,
    year: Annotated[int | None, Query(ge=2020, le=2100)] = None,
) -> Envelope[list[AdminHolidayOut]]:
    return ok(await _admin(db, actor).list_holidays(branch_id, year))


@admin_router.post(
    "/holidays", status_code=status.HTTP_201_CREATED, summary="Add a holiday", responses=_ERR
)
async def create_holiday(body: HolidayIn, actor: Manager, db: Db) -> Envelope[AdminHolidayOut]:
    return ok(await _admin(db, actor).create_holiday(body))


@admin_router.delete(
    "/holidays/{holiday_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a holiday",
    responses=_ERR,
)
async def delete_holiday(holiday_id: uuid.UUID, actor: Manager, db: Db) -> Response:
    await _admin(db, actor).delete_holiday(holiday_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
