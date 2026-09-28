"""Public API of the geo module (read-only reference data)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.geo.models import Area, District, Division, Upazila


class GeoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    name_bn: str


class AreaOut(GeoOut):
    postcode: str | None


async def list_divisions(session: AsyncSession) -> list[GeoOut]:
    rows = await session.scalars(select(Division).order_by(Division.name))
    return [GeoOut.model_validate(r) for r in rows]


async def list_districts(session: AsyncSession, division_id: uuid.UUID | None) -> list[GeoOut]:
    stmt = select(District).order_by(District.name)
    if division_id:
        stmt = stmt.where(District.division_id == division_id)
    return [GeoOut.model_validate(r) for r in await session.scalars(stmt)]


async def list_upazilas(session: AsyncSession, district_id: uuid.UUID) -> list[GeoOut]:
    stmt = select(Upazila).where(Upazila.district_id == district_id).order_by(Upazila.name)
    return [GeoOut.model_validate(r) for r in await session.scalars(stmt)]


async def list_areas(session: AsyncSession, upazila_id: uuid.UUID) -> list[AreaOut]:
    stmt = select(Area).where(Area.upazila_id == upazila_id).order_by(Area.name)
    return [AreaOut.model_validate(r) for r in await session.scalars(stmt)]


async def names_by_id(
    session: AsyncSession,
    *,
    district_ids: Iterable[uuid.UUID] = (),
    upazila_ids: Iterable[uuid.UUID] = (),
    area_ids: Iterable[uuid.UUID] = (),
) -> dict[uuid.UUID, GeoOut]:
    """Bulk lookup used by other modules to label addresses (one query per level)."""
    out: dict[uuid.UUID, GeoOut] = {}
    levels: tuple[tuple[Any, Iterable[uuid.UUID]], ...] = (
        (District, district_ids),
        (Upazila, upazila_ids),
        (Area, area_ids),
    )
    for model, ids in levels:
        wanted = {i for i in ids if i is not None}
        if wanted:
            rows: Iterable[Any] = await session.scalars(select(model).where(model.id.in_(wanted)))
            for row in rows:
                out[row.id] = GeoOut.model_validate(row)
    return out


async def validate_hierarchy(
    session: AsyncSession,
    district_id: uuid.UUID,
    upazila_id: uuid.UUID | None,
    area_id: uuid.UUID | None,
) -> str | None:
    """Return the name of the first inconsistent field, or None when the chain is valid."""
    if await session.get(District, district_id) is None:
        return "district_id"
    if upazila_id is not None:
        upazila = await session.get(Upazila, upazila_id)
        if upazila is None or upazila.district_id != district_id:
            return "upazila_id"
    if area_id is not None:
        area = await session.get(Area, area_id)
        if area is None or upazila_id is None or area.upazila_id != upazila_id:
            return "area_id"
    return None
