"""Centre module request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.phone import InvalidPhone, normalize_bd_phone
from app.core.text import CODE_PATTERN, SLUG_PATTERN
from app.modules.centre.models import CENTRE_SERVICES, CENTRE_TYPES
from app.modules.geo.service import GeoOut

CentreType = Literal["BRANCH_CENTRE", "COLLECTION_POINT", "PARTNER"]
CentreService = Literal[
    "SAMPLE_COLLECTION",
    "HOME_COLLECTION",
    "REPORT_DELIVERY",
    "ECG",
    "X_RAY",
    "ULTRASOUND",
    "DOCTOR_CHAMBER",
]
assert set(CentreType.__args__) == set(CENTRE_TYPES)  # type: ignore[attr-defined]
assert set(CentreService.__args__) == set(CENTRE_SERVICES)  # type: ignore[attr-defined]

Code = Annotated[str, Field(min_length=2, max_length=40, pattern=CODE_PATTERN)]
Slug = Annotated[str, Field(min_length=2, max_length=120, pattern=SLUG_PATTERN)]


def _phone(v: str | None) -> str | None:
    if v is None or not v.strip():
        return None
    try:
        return normalize_bd_phone(v)
    except InvalidPhone as exc:
        raise ValueError(str(exc)) from exc


OptionalPhone = Annotated[str | None, AfterValidator(_phone)]


# ---------------------------------------------------------------- public
class HoursOut(BaseModel):
    weekday: int = Field(description="0 = Monday … 6 = Sunday")
    opens_at: time
    closes_at: time


class CentreSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    name_bn: str | None
    type: CentreType
    address: str
    address_bn: str | None
    landmark: str | None
    district: GeoOut
    upazila: GeoOut | None
    area: GeoOut | None
    latitude: float | None
    longitude: float | None
    phone: str | None
    services: list[CentreService]
    open_now: bool
    closed_today_reason: str | None = Field(
        default=None, description="Holiday name when the centre is closed for a holiday today"
    )
    today_hours: list[HoursOut]
    distance_km: float | None = None


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date
    name: str
    name_bn: str | None


class CentreDetail(CentreSummary):
    email: str | None
    description: str | None
    description_bn: str | None
    hours: list[HoursOut]
    upcoming_holidays: list[HolidayOut]
    updated_at: datetime


# ---------------------------------------------------------------- admin
class BranchIn(BaseModel):
    code: Code
    name: str = Field(min_length=2, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    is_active: bool = True


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    name_bn: str | None
    is_active: bool
    version: int


class LabIn(BaseModel):
    code: Code
    name: str = Field(min_length=2, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    branch_id: uuid.UUID
    is_active: bool = True


class LabUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None


class LabOut(BranchOut):
    branch_id: uuid.UUID


class HoursIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    opens_at: time
    closes_at: time

    @model_validator(mode="after")
    def _order(self) -> HoursIn:
        if self.opens_at >= self.closes_at:
            raise ValueError("opens_at must be before closes_at")
        return self


def _validate_hours(hours: list[HoursIn]) -> list[HoursIn]:
    by_day: dict[int, list[HoursIn]] = {}
    for h in hours:
        by_day.setdefault(h.weekday, []).append(h)
    for day in by_day.values():
        day.sort(key=lambda h: h.opens_at)
        for a, b in pairwise(day):
            if b.opens_at < a.closes_at:
                raise ValueError("opening hours overlap on the same weekday")
    return hours


class _CentreFields(BaseModel):
    name_bn: str | None = Field(default=None, max_length=150)
    type: CentreType = "BRANCH_CENTRE"
    lab_id: uuid.UUID | None = None
    address_bn: str | None = Field(default=None, max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    upazila_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    latitude: float | None = Field(default=None, ge=20.3, le=26.8, description="Within BD")
    longitude: float | None = Field(default=None, ge=88.0, le=92.8, description="Within BD")
    phone: OptionalPhone = None
    email: EmailStr | None = None
    services: list[CentreService] = Field(default_factory=list, max_length=len(CENTRE_SERVICES))
    description: str | None = Field(default=None, max_length=4000)
    description_bn: str | None = Field(default=None, max_length=4000)
    is_active: bool = True

    @field_validator("services")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class CentreIn(_CentreFields):
    code: Code
    slug: Slug
    name: str = Field(min_length=2, max_length=150)
    branch_id: uuid.UUID
    address: str = Field(min_length=5, max_length=300)
    district_id: uuid.UUID
    hours: Annotated[list[HoursIn], AfterValidator(_validate_hours)] = Field(
        default_factory=list, max_length=28
    )


class CentreUpdate(BaseModel):
    """Partial update: only fields present in the body change. `hours` replaces the week."""

    slug: Slug | None = None
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    type: CentreType | None = None
    lab_id: uuid.UUID | None = None
    address: str | None = Field(default=None, min_length=5, max_length=300)
    address_bn: str | None = Field(default=None, max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    district_id: uuid.UUID | None = None
    upazila_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    latitude: float | None = Field(default=None, ge=20.3, le=26.8)
    longitude: float | None = Field(default=None, ge=88.0, le=92.8)
    phone: OptionalPhone = None
    email: EmailStr | None = None
    services: list[CentreService] | None = None
    description: str | None = Field(default=None, max_length=4000)
    description_bn: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None
    hours: Annotated[list[HoursIn], AfterValidator(_validate_hours)] | None = Field(
        default=None, max_length=28
    )


class AdminCentreOut(BaseModel):
    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    type: CentreType
    branch_id: uuid.UUID
    lab_id: uuid.UUID | None
    address: str
    address_bn: str | None
    landmark: str | None
    district_id: uuid.UUID
    upazila_id: uuid.UUID | None
    area_id: uuid.UUID | None
    latitude: float | None
    longitude: float | None
    phone: str | None
    email: str | None
    services: list[str]
    description: str | None
    description_bn: str | None
    is_active: bool
    hours: list[HoursOut]
    version: int
    updated_at: datetime


class HolidayIn(BaseModel):
    branch_id: uuid.UUID
    date: date
    name: str = Field(min_length=2, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)


class AdminHolidayOut(HolidayOut):
    branch_id: uuid.UUID
