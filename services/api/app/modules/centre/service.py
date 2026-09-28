"""Public API of the centre module: the centre locator, centre admin, and lookups other
modules may use (branch resolution, search, sitemap)."""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import SEARCH_NAMESPACE, bump_namespace
from app.core.db import on_commit
from app.core.errors import Conflict, ErrorDetail, NotFound, ValidationFailed
from app.core.scopes import register_scope_resolver
from app.core.sql import check_version, escape_like, nfc
from app.core.timeutil import dhaka_now, utcnow
from app.modules.audit import service as audit
from app.modules.centre.models import Branch, Centre, CentreHours, Holiday, Lab
from app.modules.centre.schemas import (
    AdminCentreOut,
    AdminHolidayOut,
    BranchIn,
    BranchOut,
    BranchUpdate,
    CentreDetail,
    CentreIn,
    CentreSummary,
    CentreUpdate,
    HolidayIn,
    HolidayOut,
    HoursIn,
    HoursOut,
    LabIn,
    LabOut,
    LabUpdate,
)
from app.modules.geo import service as geo


# ---------------------------------------------------------------- scope validation
async def _branch_exists(session: AsyncSession, branch_id: uuid.UUID) -> bool:
    return await session.get(Branch, branch_id) is not None


async def _lab_exists(session: AsyncSession, lab_id: uuid.UUID) -> bool:
    return await session.get(Lab, lab_id) is not None


register_scope_resolver("BRANCH", _branch_exists)
register_scope_resolver("LAB", _lab_exists)


# ---------------------------------------------------------------- helpers
def _visible() -> list[Any]:
    return [Centre.is_active.is_(True), Centre.deleted_at.is_(None)]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _hours(rows: Sequence[CentreHours]) -> list[HoursOut]:
    return [HoursOut(weekday=h.weekday, opens_at=h.opens_at, closes_at=h.closes_at) for h in rows]


def is_open(hours: Sequence[CentreHours], now: datetime, *, holiday: bool) -> bool:
    """`now` must be Bangladesh local time."""
    if holiday:
        return False
    t = now.time().replace(tzinfo=None)
    return any(h.weekday == now.weekday() and h.opens_at <= t < h.closes_at for h in hours)


@dataclass(frozen=True, slots=True)
class CentreFilters:
    q: str | None = None
    district_id: uuid.UUID | None = None
    upazila_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    service: str | None = None
    open_now: bool = False
    lat: float | None = None
    lng: float | None = None
    radius_km: float | None = None


class CentreService:
    """Public reads. The catalogue is small (tens to a few hundred centres), so open-now
    and distance filters run in Python on the matching rows before pagination."""

    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def _holidays_today(
        self, branch_ids: set[uuid.UUID], today: date
    ) -> dict[uuid.UUID, str]:
        if not branch_ids:
            return {}
        rows = await self.s.scalars(
            select(Holiday).where(Holiday.branch_id.in_(branch_ids), Holiday.date == today)
        )
        return {h.branch_id: h.name for h in rows}

    async def _summaries(
        self, centres: Sequence[Centre], *, lat: float | None, lng: float | None
    ) -> list[CentreSummary]:
        now = dhaka_now()
        holidays = await self._holidays_today({c.branch_id for c in centres}, now.date())
        names = await geo.names_by_id(
            self.s,
            district_ids=[c.district_id for c in centres],
            upazila_ids=[c.upazila_id for c in centres if c.upazila_id],
            area_ids=[c.area_id for c in centres if c.area_id],
        )
        out = []
        for c in centres:
            holiday = holidays.get(c.branch_id)
            distance = None
            if (
                lat is not None
                and lng is not None
                and c.latitude is not None
                and c.longitude is not None
            ):
                distance = round(haversine_km(lat, lng, float(c.latitude), float(c.longitude)), 2)
            out.append(
                CentreSummary(
                    id=c.id,
                    slug=c.slug,
                    name=c.name,
                    name_bn=c.name_bn,
                    type=c.type,
                    address=c.address,
                    address_bn=c.address_bn,
                    landmark=c.landmark,
                    district=names[c.district_id],
                    upazila=names.get(c.upazila_id) if c.upazila_id else None,
                    area=names.get(c.area_id) if c.area_id else None,
                    latitude=float(c.latitude) if c.latitude is not None else None,
                    longitude=float(c.longitude) if c.longitude is not None else None,
                    phone=c.phone,
                    services=list(c.services),
                    open_now=is_open(c.hours, now, holiday=holiday is not None),
                    closed_today_reason=holiday,
                    today_hours=_hours([h for h in c.hours if h.weekday == now.weekday()]),
                    distance_km=distance,
                )
            )
        return out

    async def list_centres(
        self, f: CentreFilters, *, page: int, page_size: int
    ) -> tuple[list[CentreSummary], int]:
        stmt = select(Centre).where(*_visible()).options(selectinload(Centre.hours))
        if f.district_id:
            stmt = stmt.where(Centre.district_id == f.district_id)
        if f.upazila_id:
            stmt = stmt.where(Centre.upazila_id == f.upazila_id)
        if f.area_id:
            stmt = stmt.where(Centre.area_id == f.area_id)
        if f.service:
            stmt = stmt.where(Centre.services.contains([f.service]))
        if f.q:
            like = f"%{escape_like(f.q.strip().lower())}%"
            stmt = stmt.where(
                or_(
                    func.lower(Centre.name).like(like, escape="\\"),
                    func.lower(Centre.address).like(like, escape="\\"),
                    nfc(Centre.name_bn).like(like, escape="\\"),
                    func.lower(func.coalesce(Centre.landmark, "")).like(like, escape="\\"),
                )
            )
        centres = list(await self.s.scalars(stmt.order_by(Centre.name)))
        summaries = await self._summaries(centres, lat=f.lat, lng=f.lng)
        if f.open_now:
            summaries = [c for c in summaries if c.open_now]
        if f.lat is not None and f.lng is not None:
            if f.radius_km is not None:
                summaries = [
                    c
                    for c in summaries
                    if c.distance_km is not None and c.distance_km <= f.radius_km
                ]
            summaries.sort(key=lambda c: (c.distance_km is None, c.distance_km or 0.0))
        total = len(summaries)
        start = (page - 1) * page_size
        return summaries[start : start + page_size], total

    async def get_centre(self, slug: str) -> CentreDetail:
        centre = await self.s.scalar(
            select(Centre)
            .where(Centre.slug == slug, *_visible())
            .options(selectinload(Centre.hours))
        )
        if centre is None:
            raise NotFound()
        summary = (await self._summaries([centre], lat=None, lng=None))[0]
        today = dhaka_now().date()
        holidays = await self.s.scalars(
            select(Holiday)
            .where(
                Holiday.branch_id == centre.branch_id,
                Holiday.date >= today,
                Holiday.date <= today + timedelta(days=60),
            )
            .order_by(Holiday.date)
        )
        return CentreDetail(
            **summary.model_dump(),
            email=centre.email,
            description=centre.description,
            description_bn=centre.description_bn,
            hours=_hours(centre.hours),
            upcoming_holidays=[HolidayOut.model_validate(h) for h in holidays],
            updated_at=centre.updated_at,
        )

    async def search(self, q: str, limit: int) -> list[CentreSummary]:
        """Name/area/address match with trigram typo tolerance (used by global search)."""
        like = f"%{escape_like(q)}%"
        similarity = func.similarity(func.lower(Centre.name), q)
        stmt = (
            select(Centre)
            .where(
                *_visible(),
                or_(
                    func.lower(Centre.name).like(like, escape="\\"),
                    func.lower(Centre.name).op("%")(q),
                    func.lower(Centre.address).like(like, escape="\\"),
                    nfc(Centre.name_bn).like(like, escape="\\"),
                ),
            )
            .options(selectinload(Centre.hours))
            .order_by(similarity.desc(), Centre.name)
            .limit(limit)
        )
        return await self._summaries(list(await self.s.scalars(stmt)), lat=None, lng=None)

    async def sitemap_entries(self) -> list[tuple[str, datetime]]:
        rows = await self.s.execute(select(Centre.slug, Centre.updated_at).where(*_visible()))
        return [(slug, updated) for slug, updated in rows]


async def branch_of_centre(session: AsyncSession, centre_id: uuid.UUID) -> uuid.UUID | None:
    return await session.scalar(select(Centre.branch_id).where(Centre.id == centre_id))


async def branch_ids(session: AsyncSession) -> set[uuid.UUID]:
    return set(await session.scalars(select(Branch.id)))


# ---------------------------------------------------------------- admin
def _centre_out(c: Centre) -> AdminCentreOut:
    return AdminCentreOut(
        id=c.id,
        code=c.code,
        slug=c.slug,
        name=c.name,
        name_bn=c.name_bn,
        type=c.type,
        branch_id=c.branch_id,
        lab_id=c.lab_id,
        address=c.address,
        address_bn=c.address_bn,
        landmark=c.landmark,
        district_id=c.district_id,
        upazila_id=c.upazila_id,
        area_id=c.area_id,
        latitude=float(c.latitude) if c.latitude is not None else None,
        longitude=float(c.longitude) if c.longitude is not None else None,
        phone=c.phone,
        email=c.email,
        services=list(c.services),
        description=c.description,
        description_bn=c.description_bn,
        is_active=c.is_active,
        hours=_hours(c.hours),
        version=c.version,
        updated_at=c.updated_at,
    )


def _snapshot(obj: object, fields: Sequence[str]) -> dict[str, Any]:
    return {f: getattr(obj, f) for f in fields}


class CentreAdminService:
    def __init__(self, session: AsyncSession, actor_id: uuid.UUID, actor_roles: list[str]) -> None:
        self.s = session
        self.actor_id = actor_id
        self.actor_roles = actor_roles
        self._invalidation_queued = False

    def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: object,
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
    ) -> None:
        audit.record(
            self.s,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_user_id=self.actor_id,
            actor_roles=self.actor_roles,
            before=before,
            after=after,
        )
        if not self._invalidation_queued:
            on_commit(self.s, lambda: bump_namespace(SEARCH_NAMESPACE))
            self._invalidation_queued = True

    async def _flush(self, duplicate_message: str) -> None:
        try:
            await self.s.flush()
        except IntegrityError as exc:
            raise Conflict(duplicate_message, code="DUPLICATE") from exc

    # branches ---------------------------------------------------------------
    async def list_branches(self) -> list[BranchOut]:
        rows = await self.s.scalars(select(Branch).order_by(Branch.name))
        return [BranchOut.model_validate(b) for b in rows]

    async def create_branch(self, body: BranchIn) -> BranchOut:
        branch = Branch(**body.model_dump())
        self.s.add(branch)
        await self._flush("A branch with this code already exists.")
        self._audit("branch.created", "branch", branch.id, after=body.model_dump())
        return BranchOut.model_validate(branch)

    async def update_branch(
        self, branch_id: uuid.UUID, body: BranchUpdate, if_match: int | None
    ) -> BranchOut:
        branch = await self.s.get(Branch, branch_id, with_for_update=True)
        if branch is None:
            raise NotFound()
        check_version(branch.version, if_match)
        changes = body.model_dump(exclude_unset=True)
        before = _snapshot(branch, list(changes))
        for k, v in changes.items():
            setattr(branch, k, v)
        branch.version += 1
        await self._flush("Duplicate branch.")
        self._audit("branch.updated", "branch", branch.id, before=before, after=changes)
        return BranchOut.model_validate(branch)

    # labs -------------------------------------------------------------------
    async def list_labs(self) -> list[LabOut]:
        rows = await self.s.scalars(select(Lab).order_by(Lab.name))
        return [LabOut.model_validate(lab) for lab in rows]

    async def create_lab(self, body: LabIn) -> LabOut:
        if not await _branch_exists(self.s, body.branch_id):
            raise ValidationFailed(details=[ErrorDetail(field="branch_id", issue="unknown branch")])
        lab = Lab(**body.model_dump())
        self.s.add(lab)
        await self._flush("A lab with this code already exists.")
        self._audit("lab.created", "lab", lab.id, after=body.model_dump())
        return LabOut.model_validate(lab)

    async def update_lab(self, lab_id: uuid.UUID, body: LabUpdate, if_match: int | None) -> LabOut:
        lab = await self.s.get(Lab, lab_id, with_for_update=True)
        if lab is None:
            raise NotFound()
        check_version(lab.version, if_match)
        changes = body.model_dump(exclude_unset=True)
        before = _snapshot(lab, list(changes))
        for k, v in changes.items():
            setattr(lab, k, v)
        lab.version += 1
        self._audit("lab.updated", "lab", lab.id, before=before, after=changes)
        return LabOut.model_validate(lab)

    # centres ----------------------------------------------------------------
    async def _load(self, centre_id: uuid.UUID, *, lock: bool = False) -> Centre:
        stmt = (
            select(Centre)
            .where(Centre.id == centre_id, Centre.deleted_at.is_(None))
            .options(selectinload(Centre.hours))
            .execution_options(populate_existing=True)
        )
        if lock:
            stmt = stmt.with_for_update()
        centre = await self.s.scalar(stmt)
        if centre is None:
            raise NotFound()
        return centre

    async def _validate_refs(
        self,
        *,
        branch_id: uuid.UUID,
        lab_id: uuid.UUID | None,
        district_id: uuid.UUID,
        upazila_id: uuid.UUID | None,
        area_id: uuid.UUID | None,
    ) -> None:
        details = []
        if not await _branch_exists(self.s, branch_id):
            details.append(ErrorDetail(field="branch_id", issue="unknown branch"))
        if lab_id is not None and not await _lab_exists(self.s, lab_id):
            details.append(ErrorDetail(field="lab_id", issue="unknown lab"))
        bad = await geo.validate_hierarchy(self.s, district_id, upazila_id, area_id)
        if bad:
            details.append(ErrorDetail(field=bad, issue="not part of the selected location"))
        if details:
            raise ValidationFailed(details=details)

    @staticmethod
    def _hours_rows(hours: Sequence[HoursIn]) -> list[CentreHours]:
        return [
            CentreHours(weekday=h.weekday, opens_at=h.opens_at, closes_at=h.closes_at)
            for h in hours
        ]

    async def list_centres(
        self, *, q: str | None, branch_id: uuid.UUID | None, include_inactive: bool
    ) -> list[AdminCentreOut]:
        stmt = (
            select(Centre)
            .where(Centre.deleted_at.is_(None))
            .options(selectinload(Centre.hours))
            .order_by(Centre.name)
        )
        if not include_inactive:
            stmt = stmt.where(Centre.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Centre.branch_id == branch_id)
        if q:
            like = f"%{escape_like(q.strip().lower())}%"
            stmt = stmt.where(
                or_(
                    func.lower(Centre.name).like(like, escape="\\"),
                    func.lower(Centre.code).like(like, escape="\\"),
                )
            )
        return [_centre_out(c) for c in await self.s.scalars(stmt)]

    async def get_centre(self, centre_id: uuid.UUID) -> AdminCentreOut:
        return _centre_out(await self._load(centre_id))

    async def create_centre(self, body: CentreIn) -> AdminCentreOut:
        await self._validate_refs(
            branch_id=body.branch_id,
            lab_id=body.lab_id,
            district_id=body.district_id,
            upazila_id=body.upazila_id,
            area_id=body.area_id,
        )
        data = body.model_dump(exclude={"hours"})
        centre = Centre(**data, hours=self._hours_rows(body.hours))
        self.s.add(centre)
        await self._flush("A centre with this code or slug already exists.")
        self._audit(
            "centre.created",
            "centre",
            centre.id,
            after={**data, "hours": [h.model_dump(mode="json") for h in body.hours]},
        )
        return _centre_out(await self._load(centre.id))

    async def update_centre(
        self, centre_id: uuid.UUID, body: CentreUpdate, if_match: int | None
    ) -> AdminCentreOut:
        centre = await self._load(centre_id, lock=True)
        check_version(centre.version, if_match)
        changes = body.model_dump(exclude_unset=True, exclude={"hours"})
        before = _snapshot(centre, list(changes))
        for k, v in changes.items():
            setattr(centre, k, v)
        await self._validate_refs(
            branch_id=centre.branch_id,
            lab_id=centre.lab_id,
            district_id=centre.district_id,
            upazila_id=centre.upazila_id,
            area_id=centre.area_id,
        )
        after: dict[str, Any] = dict(changes)
        if body.hours is not None:
            before["hours"] = [h.model_dump(mode="json") for h in _hours(centre.hours)]
            # Delete then insert: the new week may reuse primary keys of the old rows.
            for old in centre.hours:
                await self.s.delete(old)
            await self.s.flush()
            for row in self._hours_rows(body.hours):
                row.centre_id = centre.id
                self.s.add(row)
            after["hours"] = [h.model_dump(mode="json") for h in body.hours]
        centre.version += 1
        await self._flush("A centre with this slug already exists.")
        self._audit("centre.updated", "centre", centre.id, before=before, after=after)
        return _centre_out(await self._load(centre.id))

    async def delete_centre(self, centre_id: uuid.UUID, if_match: int | None) -> None:
        centre = await self._load(centre_id, lock=True)
        check_version(centre.version, if_match)
        centre.deleted_at = utcnow()
        centre.is_active = False
        centre.version += 1
        self._audit("centre.deleted", "centre", centre.id, before={"slug": centre.slug})

    # holidays ---------------------------------------------------------------
    async def list_holidays(
        self, branch_id: uuid.UUID | None, year: int | None
    ) -> list[AdminHolidayOut]:
        stmt = select(Holiday).order_by(Holiday.date)
        if branch_id:
            stmt = stmt.where(Holiday.branch_id == branch_id)
        if year:
            stmt = stmt.where(Holiday.date >= date(year, 1, 1), Holiday.date <= date(year, 12, 31))
        return [AdminHolidayOut.model_validate(h) for h in await self.s.scalars(stmt)]

    async def create_holiday(self, body: HolidayIn) -> AdminHolidayOut:
        if not await _branch_exists(self.s, body.branch_id):
            raise ValidationFailed(details=[ErrorDetail(field="branch_id", issue="unknown branch")])
        holiday = Holiday(**body.model_dump())
        self.s.add(holiday)
        await self._flush("This branch already has a holiday on that date.")
        self._audit("holiday.created", "holiday", holiday.id, after=body.model_dump(mode="json"))
        return AdminHolidayOut.model_validate(holiday)

    async def delete_holiday(self, holiday_id: uuid.UUID) -> None:
        holiday = await self.s.get(Holiday, holiday_id)
        if holiday is None:
            raise NotFound()
        self._audit(
            "holiday.deleted",
            "holiday",
            holiday.id,
            before={
                "branch_id": holiday.branch_id,
                "date": str(holiday.date),
                "name": holiday.name,
            },
        )
        await self.s.delete(holiday)
