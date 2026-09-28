"""Catalog request/response schemas. Text fields come in English and Bangla (`*_bn`);
clients pick by locale, so responses are cacheable regardless of language."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.core.text import CODE_PATTERN, SLUG_PATTERN, normalize_query

Code = Annotated[str, Field(min_length=2, max_length=40, pattern=CODE_PATTERN)]
Slug = Annotated[str, Field(min_length=2, max_length=120, pattern=SLUG_PATTERN)]
Name = Annotated[str, Field(min_length=2, max_length=200)]
NameBn = Annotated[str | None, Field(default=None, max_length=200)]
Sex = Literal["M", "F"]
ResultType = Literal["NUMERIC", "TEXT", "OPTION", "CALCULATED"]
ItemType = Literal["TEST", "PACKAGE"]
SynonymTarget = Literal["TEST", "PACKAGE", "CONCERN"]

ConcernIcon = Literal[
    "activity",
    "baby",
    "bone",
    "brain",
    "droplet",
    "droplets",
    "heart-pulse",
    "shield-plus",
    "stethoscope",
    "sun",
    "thermometer",
    "venus",
    "mars",
    "user-round",
    "flask-conical",
    "scan-heart",
]
#: Icons the web app can draw for health concerns (keeps admin input to a safe allow-list).
CONCERN_ICONS: tuple[str, ...] = get_args(ConcernIcon)


# ================================================================= public
class Price(BaseModel):
    """Money in poisha (1/100 BDT)."""

    amount: int
    mrp: int
    currency: Literal["BDT"] = "BDT"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def discount_percent(self) -> int:
        if self.mrp <= 0 or self.amount >= self.mrp:
            return 0
        return round((self.mrp - self.amount) * 100 / self.mrp)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    name_bn: str | None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    name_bn: str | None
    parent_id: uuid.UUID | None


class SampleTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    name_bn: str | None
    container: str | None
    tube_colour: str | None


class PreparationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    title_bn: str | None
    instructions: str
    instructions_bn: str | None
    fasting_hours: int | None


class ConcernRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    name_bn: str | None
    icon: str


class TestSummary(BaseModel):
    __test__ = False

    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    short_description: str | None
    short_description_bn: str | None
    department: DepartmentOut
    sample_type: SampleTypeOut
    tat_hours: int
    home_collection: bool
    centre_collection: bool
    fasting_hours: int | None
    parameter_count: int
    is_featured: bool
    price: Price | None = Field(description="Null when the item has no price (not bookable)")


class ParameterPublic(BaseModel):
    code: str
    name: str
    name_bn: str | None
    unit: str | None


class PackageSummary(BaseModel):
    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    short_description: str | None
    short_description_bn: str | None
    test_count: int
    parameter_count: int
    sex: Sex | None
    age_min_years: int | None
    age_max_years: int | None
    fasting_hours: int | None
    home_collection: bool
    is_featured: bool
    price: Price | None
    tests_total: int | None = Field(
        description="Sum of the included tests' individual prices (poisha), when all are priced"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def savings(self) -> int | None:
        """How much cheaper the package is than booking its tests separately."""
        if self.price is None or self.tests_total is None:
            return None
        return max(self.tests_total - self.price.amount, 0)


class TestDetail(TestSummary):
    __test__ = False

    description: str | None
    description_bn: str | None
    category: CategoryOut | None
    sample_volume: str | None
    preparation: PreparationOut | None
    parameters: list[ParameterPublic]
    concerns: list[ConcernRef]
    packages: list[PackageSummary] = Field(description="Packages that include this test")
    seo_title: str | None
    seo_description: str | None
    updated_at: datetime


class PackageDetail(PackageSummary):
    description: str | None
    description_bn: str | None
    tests: list[TestSummary]
    concerns: list[ConcernRef]
    preparations: list[PreparationOut]
    seo_title: str | None
    seo_description: str | None
    updated_at: datetime


class ConcernSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    name_bn: str | None
    icon: str
    description: str | None
    description_bn: str | None
    is_featured: bool
    test_count: int
    package_count: int


class ConcernDetail(ConcernSummary):
    tests: list[TestSummary]
    packages: list[PackageSummary]
    seo_title: str | None
    seo_description: str | None
    updated_at: datetime


class CatalogFilters(BaseModel):
    """Facets for the test list filters."""

    departments: list[DepartmentOut]
    categories: list[CategoryOut]
    sample_types: list[SampleTypeOut]
    concerns: list[ConcernRef]


class Suggestion(BaseModel):
    type: Literal["test", "package", "concern", "centre"]
    slug: str
    name: str
    name_bn: str | None
    price: Price | None = None


class SitemapEntry(BaseModel):
    type: Literal["test", "package", "concern", "centre", "page"]
    slug: str
    updated_at: datetime


# ================================================================= admin
class _MasterBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    name_bn: str | None = Field(default=None, max_length=120)
    is_active: bool = True


class DepartmentIn(_MasterBase):
    code: Code
    sort_order: int = Field(default=0, ge=0, le=10_000)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    name_bn: str | None = Field(default=None, max_length=120)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None


class AdminDepartmentOut(DepartmentOut):
    sort_order: int
    is_active: bool
    version: int


class CategoryIn(_MasterBase):
    slug: Slug
    parent_id: uuid.UUID | None = None
    sort_order: int = Field(default=0, ge=0, le=10_000)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    name_bn: str | None = Field(default=None, max_length=120)
    parent_id: uuid.UUID | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None


class AdminCategoryOut(CategoryOut):
    sort_order: int
    is_active: bool
    version: int


class SampleTypeIn(_MasterBase):
    code: Code
    container: str | None = Field(default=None, max_length=120)
    tube_colour: str | None = Field(default=None, max_length=40)
    default_volume_ml: Decimal | None = Field(default=None, gt=0, le=1000)


class SampleTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    name_bn: str | None = Field(default=None, max_length=120)
    container: str | None = Field(default=None, max_length=120)
    tube_colour: str | None = Field(default=None, max_length=40)
    default_volume_ml: Decimal | None = Field(default=None, gt=0, le=1000)
    is_active: bool | None = None


class AdminSampleTypeOut(SampleTypeOut):
    default_volume_ml: Decimal | None
    is_active: bool
    version: int


class PreparationIn(BaseModel):
    code: Code
    title: str = Field(min_length=2, max_length=150)
    title_bn: str | None = Field(default=None, max_length=150)
    instructions: str = Field(min_length=2, max_length=2000)
    instructions_bn: str | None = Field(default=None, max_length=2000)
    fasting_hours: int | None = Field(default=None, ge=0, le=24)
    is_active: bool = True


class PreparationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    title_bn: str | None = Field(default=None, max_length=150)
    instructions: str | None = Field(default=None, min_length=2, max_length=2000)
    instructions_bn: str | None = Field(default=None, max_length=2000)
    fasting_hours: int | None = Field(default=None, ge=0, le=24)
    is_active: bool | None = None


class AdminPreparationOut(PreparationOut):
    is_active: bool
    version: int


# ---------------------------------------------------------------- tests
class _TestFields(BaseModel):
    name_bn: NameBn = None
    aliases: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, max_length=300)
    short_description_bn: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    description_bn: str | None = Field(default=None, max_length=8000)
    category_id: uuid.UUID | None = None
    sample_volume: str | None = Field(default=None, max_length=40)
    preparation_id: uuid.UUID | None = None
    home_collection: bool = True
    centre_collection: bool = True
    is_featured: bool = False
    popularity: int = Field(default=0, ge=0, le=1_000_000)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=170)
    is_active: bool = True


class TestIn(_TestFields):
    __test__ = False

    code: Code
    slug: Slug
    name: Name
    department_id: uuid.UUID
    sample_type_id: uuid.UUID
    tat_hours: int = Field(gt=0, le=24 * 60)

    @model_validator(mode="after")
    def _collection(self) -> TestIn:
        if not (self.home_collection or self.centre_collection):
            raise ValueError("a test needs home or centre collection")
        return self


class TestUpdate(BaseModel):
    __test__ = False

    slug: Slug | None = None
    name: Name | None = None
    name_bn: NameBn = None
    aliases: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, max_length=300)
    short_description_bn: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    description_bn: str | None = Field(default=None, max_length=8000)
    department_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    sample_type_id: uuid.UUID | None = None
    sample_volume: str | None = Field(default=None, max_length=40)
    preparation_id: uuid.UUID | None = None
    tat_hours: int | None = Field(default=None, gt=0, le=24 * 60)
    home_collection: bool | None = None
    centre_collection: bool | None = None
    is_featured: bool | None = None
    popularity: int | None = Field(default=None, ge=0, le=1_000_000)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=170)
    is_active: bool | None = None


class ReferenceRangeIn(BaseModel):
    sex: Sex | None = None
    age_min_days: int = Field(default=0, ge=0, le=365 * 130)
    age_max_days: int | None = Field(default=None, gt=0, le=365 * 130)
    sample_type_id: uuid.UUID | None = None
    lab_id: uuid.UUID | None = None
    method: str | None = Field(default=None, max_length=80)
    low: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    high: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    critical_low: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    critical_high: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    text_normal: str | None = Field(default=None, max_length=120)
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("method", "text_normal", "notes")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None

    @model_validator(mode="after")
    def _consistent(self) -> ReferenceRangeIn:
        if self.age_max_days is not None and self.age_max_days <= self.age_min_days:
            raise ValueError("age_max_days must be greater than age_min_days")
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("low must not exceed high")
        if self.critical_low is not None and self.low is not None and self.critical_low > self.low:
            raise ValueError("critical_low must not exceed low")
        if (
            self.critical_high is not None
            and self.high is not None
            and self.critical_high < self.high
        ):
            raise ValueError("critical_high must not be below high")
        if self.low is None and self.high is None and self.text_normal is None:
            raise ValueError("give low and/or high, or a text normal value")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to <= self.effective_from
        ):
            raise ValueError("effective_to must be after effective_from")
        return self


class ReferenceRangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sex: str | None
    age_min_days: int
    age_max_days: int | None
    sample_type_id: uuid.UUID | None
    lab_id: uuid.UUID | None
    method: str | None
    low: Decimal | None
    high: Decimal | None
    critical_low: Decimal | None
    critical_high: Decimal | None
    text_normal: str | None
    effective_from: date
    effective_to: date | None
    notes: str | None
    version: int


class ParameterIn(BaseModel):
    code: Code
    name: str = Field(min_length=1, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    unit: str | None = Field(default=None, max_length=40)
    result_type: ResultType = "NUMERIC"
    decimals: int = Field(default=1, ge=0, le=6)
    formula: str | None = Field(default=None, max_length=300)
    options: list[Annotated[str, Field(min_length=1, max_length=60)]] | None = Field(
        default=None, max_length=30
    )
    loinc: str | None = Field(default=None, max_length=20, pattern=r"^\d{1,7}-\d$")
    display_order: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = True

    @model_validator(mode="after")
    def _type_rules(self) -> ParameterIn:
        if (self.result_type == "CALCULATED") != bool(self.formula):
            raise ValueError("formula is required for, and only for, CALCULATED parameters")
        if self.result_type == "OPTION" and not self.options:
            raise ValueError("OPTION parameters need at least one option")
        if self.result_type != "OPTION":
            self.options = None
        return self


class ParameterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    name_bn: str | None = Field(default=None, max_length=150)
    unit: str | None = Field(default=None, max_length=40)
    decimals: int | None = Field(default=None, ge=0, le=6)
    formula: str | None = Field(default=None, max_length=300)
    options: list[Annotated[str, Field(min_length=1, max_length=60)]] | None = Field(
        default=None, max_length=30
    )
    loinc: str | None = Field(default=None, max_length=20, pattern=r"^\d{1,7}-\d$")
    display_order: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None


class ParameterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    name_bn: str | None
    unit: str | None
    result_type: str
    decimals: int
    formula: str | None
    options: list[str] | None
    loinc: str | None
    display_order: int
    is_active: bool
    ranges: list[ReferenceRangeOut]


class ItemPrice(BaseModel):
    price_list_id: uuid.UUID
    price_list_code: str
    price_list_name: str
    branch_id: uuid.UUID | None
    price: Price
    effective_from: datetime


class AdminTestListItem(BaseModel):
    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    department: DepartmentOut
    sample_type: SampleTypeOut
    tat_hours: int
    parameter_count: int
    is_active: bool
    is_featured: bool
    price: Price | None = Field(description="Current default price-list price")
    version: int
    updated_at: datetime


class AdminTestOut(BaseModel):
    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    aliases: str | None
    short_description: str | None
    short_description_bn: str | None
    description: str | None
    description_bn: str | None
    department_id: uuid.UUID
    category_id: uuid.UUID | None
    sample_type_id: uuid.UUID
    sample_volume: str | None
    preparation_id: uuid.UUID | None
    tat_hours: int
    home_collection: bool
    centre_collection: bool
    is_featured: bool
    popularity: int
    seo_title: str | None
    seo_description: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    parameters: list[ParameterOut]
    prices: list[ItemPrice]
    concern_ids: list[uuid.UUID]


# ---------------------------------------------------------------- packages
class _PackageFields(BaseModel):
    name_bn: NameBn = None
    aliases: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, max_length=300)
    short_description_bn: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    description_bn: str | None = Field(default=None, max_length=8000)
    sex: Sex | None = None
    age_min_years: int | None = Field(default=None, ge=0, le=120)
    age_max_years: int | None = Field(default=None, ge=0, le=120)
    is_featured: bool = False
    popularity: int = Field(default=0, ge=0, le=1_000_000)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=170)
    is_active: bool = True


class PackageIn(_PackageFields):
    code: Code
    slug: Slug
    name: Name
    test_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _ages(self) -> PackageIn:
        if (
            self.age_min_years is not None
            and self.age_max_years is not None
            and self.age_min_years > self.age_max_years
        ):
            raise ValueError("age_min_years must not exceed age_max_years")
        if len(set(self.test_ids)) != len(self.test_ids):
            raise ValueError("test_ids contains duplicates")
        return self


class PackageUpdate(BaseModel):
    slug: Slug | None = None
    name: Name | None = None
    name_bn: NameBn = None
    aliases: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, max_length=300)
    short_description_bn: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    description_bn: str | None = Field(default=None, max_length=8000)
    sex: Sex | None = None
    age_min_years: int | None = Field(default=None, ge=0, le=120)
    age_max_years: int | None = Field(default=None, ge=0, le=120)
    is_featured: bool | None = None
    popularity: int | None = Field(default=None, ge=0, le=1_000_000)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=170)
    is_active: bool | None = None
    test_ids: list[uuid.UUID] | None = Field(default=None, min_length=1, max_length=200)


class AdminPackageListItem(BaseModel):
    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    test_count: int
    is_active: bool
    is_featured: bool
    price: Price | None
    tests_total: int | None
    version: int
    updated_at: datetime


class AdminPackageOut(BaseModel):
    id: uuid.UUID
    code: str
    slug: str
    name: str
    name_bn: str | None
    aliases: str | None
    short_description: str | None
    short_description_bn: str | None
    description: str | None
    description_bn: str | None
    sex: str | None
    age_min_years: int | None
    age_max_years: int | None
    is_featured: bool
    popularity: int
    seo_title: str | None
    seo_description: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    test_ids: list[uuid.UUID]
    prices: list[ItemPrice]
    tests_total: int | None


# ---------------------------------------------------------------- concerns & synonyms
class ConcernIn(BaseModel):
    slug: Slug
    name: str = Field(min_length=2, max_length=120)
    name_bn: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    description_bn: str | None = Field(default=None, max_length=4000)
    icon: ConcernIcon = "activity"
    sort_order: int = Field(default=0, ge=0, le=10_000)
    is_featured: bool = False
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=170)
    is_active: bool = True
    test_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    package_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class ConcernUpdate(BaseModel):
    slug: Slug | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    name_bn: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    description_bn: str | None = Field(default=None, max_length=4000)
    icon: ConcernIcon | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_featured: bool | None = None
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=170)
    is_active: bool | None = None
    test_ids: list[uuid.UUID] | None = Field(default=None, max_length=500)
    package_ids: list[uuid.UUID] | None = Field(default=None, max_length=200)


class AdminConcernOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    name_bn: str | None
    description: str | None
    description_bn: str | None
    icon: str
    sort_order: int
    is_featured: bool
    seo_title: str | None
    seo_description: str | None
    is_active: bool
    version: int
    updated_at: datetime
    test_ids: list[uuid.UUID]
    package_ids: list[uuid.UUID]


class SynonymIn(BaseModel):
    term: str = Field(
        min_length=2,
        max_length=80,
        pattern=r"^[\wঀ-৿][\wঀ-৿ .'-]*$",
        description="Letters, digits, spaces, apostrophes and hyphens (English or Bangla)",
    )
    target_type: SynonymTarget
    target_id: uuid.UUID

    @field_validator("term", mode="before")
    @classmethod
    def _normalise(cls, v: object) -> object:
        return normalize_query(v) if isinstance(v, str) else v


class SynonymOut(BaseModel):
    id: uuid.UUID
    term: str
    target_type: SynonymTarget
    target_id: uuid.UUID
    target_name: str


# ---------------------------------------------------------------- pricing
class PriceListIn(BaseModel):
    code: Code
    name: str = Field(min_length=2, max_length=120)
    branch_id: uuid.UUID | None = Field(default=None, description="Null = the default list")
    is_active: bool = True


class PriceListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


class PriceListOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    branch_id: uuid.UUID | None
    is_active: bool
    version: int
    item_count: int


class SetPriceIn(BaseModel):
    item_type: ItemType
    item_id: uuid.UUID
    mrp: int = Field(ge=0, le=10_000_000_00, description="Poisha")
    price: int = Field(ge=0, le=10_000_000_00, description="Poisha")
    effective_from: datetime | None = Field(
        default=None, description="Future start for a scheduled change; default now"
    )

    @model_validator(mode="after")
    def _amounts(self) -> SetPriceIn:
        if self.price > self.mrp:
            raise ValueError("price must not exceed mrp")
        if self.effective_from is not None and self.effective_from.tzinfo is None:
            raise ValueError("effective_from must include a timezone")
        return self


class PriceItemOut(BaseModel):
    item_type: ItemType
    item_id: uuid.UUID
    code: str
    name: str
    is_active: bool
    current: Price | None
    current_since: datetime | None
    scheduled: Price | None = None
    scheduled_from: datetime | None = None


class PriceHistoryOut(BaseModel):
    price: Price
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
