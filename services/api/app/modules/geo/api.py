"""Public BD location lookups for address forms and the centre locator."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.responses import Envelope, ok
from app.modules.geo import service
from app.modules.geo.service import AreaOut, GeoOut

router = APIRouter(prefix="/geo", tags=["public: geography"])

Db = Annotated[AsyncSession, Depends(get_session)]

#: Reference data changes rarely; let browsers and CDNs cache it.
CACHE = "public, max-age=3600"


@router.get("/divisions", summary="List divisions", responses=error_responses(400))
async def divisions(db: Db, response: Response) -> Envelope[list[GeoOut]]:
    response.headers["Cache-Control"] = CACHE
    return ok(await service.list_divisions(db))


@router.get("/districts", summary="List districts", responses=error_responses(400))
async def districts(
    db: Db, response: Response, division_id: uuid.UUID | None = None
) -> Envelope[list[GeoOut]]:
    response.headers["Cache-Control"] = CACHE
    return ok(await service.list_districts(db, division_id))


@router.get(
    "/upazilas", summary="List upazilas/thanas of a district", responses=error_responses(400)
)
async def upazilas(db: Db, response: Response, district_id: uuid.UUID) -> Envelope[list[GeoOut]]:
    response.headers["Cache-Control"] = CACHE
    return ok(await service.list_upazilas(db, district_id))


@router.get("/areas", summary="List areas of an upazila/thana", responses=error_responses(400))
async def areas(db: Db, response: Response, upazila_id: uuid.UUID) -> Envelope[list[AreaOut]]:
    response.headers["Cache-Control"] = CACHE
    return ok(await service.list_areas(db, upazila_id))
