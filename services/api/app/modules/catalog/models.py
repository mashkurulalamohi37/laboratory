"""Catalog schema: tests, parameters, reference ranges, packages, health concerns, search
synonyms and branch price lists. All prices come from price lists (never from code)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "catalog"

RESULT_TYPES = ("NUMERIC", "TEXT", "OPTION", "CALCULATED")
ITEM_TYPES = ("TEST", "PACKAGE")
SYNONYM_TARGETS = ("TEST", "PACKAGE", "CONCERN")


def _tsvector(*weighted: tuple[str, str]) -> str:
    """Generated-column expression; 'simple' config because names mix English, Bangla and
    lab abbreviations that stemming would mangle."""
    return " || ".join(
        f"setweight(to_tsvector('simple', coalesce({col}, '')), '{w}')" for col, w in weighted
    )


class _Versioned:
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


# ---------------------------------------------------------------- master data
class Department(_Versioned, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class Category(_Versioned, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_parent_id", "parent_id"), {"schema": SCHEMA})

    id: Mapped[UUIDPk]
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(120))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.categories.id", ondelete="RESTRICT")
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class SampleType(_Versioned, TimestampMixin, Base):
    __tablename__ = "sample_types"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(120))
    container: Mapped[str | None] = mapped_column(String(120))
    tube_colour: Mapped[str | None] = mapped_column(String(40))
    default_volume_ml: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class Preparation(_Versioned, TimestampMixin, Base):
    """Reusable patient instructions, e.g. "10-12 hours fasting"."""

    __tablename__ = "preparations"
    __table_args__ = (
        CheckConstraint("fasting_hours IS NULL OR fasting_hours BETWEEN 0 AND 24", name="fasting"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    title_bn: Mapped[str | None] = mapped_column(String(150))
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    instructions_bn: Mapped[str | None] = mapped_column(Text)
    fasting_hours: Mapped[int | None] = mapped_column(SmallInteger)


# ---------------------------------------------------------------- tests
class Test(_Versioned, TimestampMixin, Base):
    __tablename__ = "tests"
    __table_args__ = (
        CheckConstraint("tat_hours > 0", name="tat_positive"),
        CheckConstraint("home_collection OR centre_collection", name="has_collection_mode"),
        Index("ix_tests_department_id", "department_id"),
        Index("ix_tests_category_id", "category_id"),
        Index("ix_tests_search_vector", "search_vector", postgresql_using="gin"),
        {"schema": SCHEMA},
    )
    __test__ = False  # not a pytest test class

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(200))
    #: Other names and abbreviations people search for (free text, space/comma separated).
    aliases: Mapped[str | None] = mapped_column(String(500))
    short_description: Mapped[str | None] = mapped_column(String(300))
    short_description_bn: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    description_bn: Mapped[str | None] = mapped_column(Text)
    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.departments.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.categories.id", ondelete="RESTRICT")
    )
    sample_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.sample_types.id", ondelete="RESTRICT"), nullable=False
    )
    sample_volume: Mapped[str | None] = mapped_column(String(40))
    preparation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.preparations.id", ondelete="RESTRICT")
    )
    tat_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    home_collection: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    centre_collection: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(170))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(
            _tsvector(("name", "A"), ("code", "A"), ("aliases", "A"), ("short_description", "C")),
            persisted=True,
        ),
    )

    parameters: Mapped[list[TestParameter]] = relationship(
        lazy="raise",
        order_by="TestParameter.display_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        back_populates="test",
    )


Index(
    "ix_tests_name_trgm",
    func.lower(Test.name).label("lower_name"),
    postgresql_using="gin",
    postgresql_ops={"lower_name": "gin_trgm_ops"},
)


class TestParameter(TimestampMixin, Base):
    __tablename__ = "test_parameters"
    __table_args__ = (
        UniqueConstraint("test_id", "code", name="uq_test_parameters_test_code"),
        CheckConstraint(f"result_type IN {RESULT_TYPES}", name="result_type_valid"),
        CheckConstraint("decimals BETWEEN 0 AND 6", name="decimals_range"),
        CheckConstraint(
            "(result_type = 'CALCULATED') = (formula IS NOT NULL)", name="formula_iff_calculated"
        ),
        {"schema": SCHEMA},
    )
    __test__ = False

    id: Mapped[UUIDPk]
    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.tests.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(150))
    unit: Mapped[str | None] = mapped_column(String(40))
    result_type: Mapped[str] = mapped_column(String(12), nullable=False, server_default="NUMERIC")
    decimals: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    formula: Mapped[str | None] = mapped_column(String(300))
    #: Allowed answers for OPTION parameters, e.g. ["Positive", "Negative"].
    options: Mapped[list[str] | None] = mapped_column(JSONB)
    loinc: Mapped[str | None] = mapped_column(String(20))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    test: Mapped[Test] = relationship(back_populates="parameters", lazy="raise")
    ranges: Mapped[list[ReferenceRange]] = relationship(
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ReferenceRange.age_min_days",
    )


class ReferenceRange(TimestampMixin, Base):
    """Reference interval for one parameter. Narrower criteria win when several match
    (lab > method > sample type > sex > age band). Overlapping ranges with identical
    criteria are rejected by an exclusion constraint (migration 0002)."""

    __tablename__ = "reference_ranges"
    __table_args__ = (
        CheckConstraint("sex IS NULL OR sex IN ('M', 'F')", name="sex_valid"),
        CheckConstraint("age_min_days >= 0", name="age_min_nonnegative"),
        CheckConstraint(
            "age_max_days IS NULL OR age_max_days > age_min_days", name="age_band_valid"
        ),
        CheckConstraint("low IS NULL OR high IS NULL OR low <= high", name="low_le_high"),
        CheckConstraint(
            "critical_low IS NULL OR low IS NULL OR critical_low <= low", name="critical_low_le_low"
        ),
        CheckConstraint(
            "critical_high IS NULL OR high IS NULL OR critical_high >= high",
            name="critical_high_ge_high",
        ),
        CheckConstraint(
            "low IS NOT NULL OR high IS NOT NULL OR text_normal IS NOT NULL", name="has_normal"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="effective_window"
        ),
        Index("ix_reference_ranges_parameter_id", "parameter_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.test_parameters.id", ondelete="CASCADE"), nullable=False
    )
    sex: Mapped[str | None] = mapped_column(String(1))
    #: Age band in days, [min, max); max NULL = no upper bound.
    age_min_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    age_max_days: Mapped[int | None] = mapped_column(Integer)
    sample_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.sample_types.id", ondelete="RESTRICT")
    )
    lab_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("centre.labs.id", ondelete="RESTRICT")
    )
    method: Mapped[str | None] = mapped_column(String(80))
    low: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    high: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    critical_low: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    critical_high: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    text_normal: Mapped[str | None] = mapped_column(String(120))
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


# ---------------------------------------------------------------- packages & concerns
class Package(_Versioned, TimestampMixin, Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("sex IS NULL OR sex IN ('M', 'F')", name="sex_valid"),
        CheckConstraint(
            "age_min_years IS NULL OR age_max_years IS NULL OR age_min_years <= age_max_years",
            name="age_band_valid",
        ),
        Index("ix_packages_search_vector", "search_vector", postgresql_using="gin"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(200))
    aliases: Mapped[str | None] = mapped_column(String(500))
    short_description: Mapped[str | None] = mapped_column(String(300))
    short_description_bn: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    description_bn: Mapped[str | None] = mapped_column(Text)
    sex: Mapped[str | None] = mapped_column(String(1))
    age_min_years: Mapped[int | None] = mapped_column(SmallInteger)
    age_max_years: Mapped[int | None] = mapped_column(SmallInteger)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(170))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(
            _tsvector(("name", "A"), ("code", "A"), ("aliases", "A"), ("short_description", "C")),
            persisted=True,
        ),
    )


Index(
    "ix_packages_name_trgm",
    func.lower(Package.name).label("lower_name"),
    postgresql_using="gin",
    postgresql_ops={"lower_name": "gin_trgm_ops"},
)


class PackageTest(Base):
    __tablename__ = "package_tests"
    __table_args__ = (Index("ix_package_tests_test_id", "test_id"), {"schema": SCHEMA})

    package_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.packages.id", ondelete="CASCADE"), primary_key=True
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.tests.id", ondelete="RESTRICT"), primary_key=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class HealthConcern(_Versioned, TimestampMixin, Base):
    """Patient-friendly taxonomy ("Diabetes", "Thyroid"), mapped to tests and packages."""

    __tablename__ = "health_concerns"
    __table_args__ = (
        Index("ix_health_concerns_search_vector", "search_vector", postgresql_using="gin"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    description_bn: Mapped[str | None] = mapped_column(Text)
    #: Icon key understood by the web app (a fixed allow-list, see schemas.CONCERN_ICONS).
    icon: Mapped[str] = mapped_column(String(40), nullable=False, server_default="activity")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(170))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(_tsvector(("name", "A"), ("description", "C")), persisted=True),
    )


class ConcernTest(Base):
    __tablename__ = "concern_tests"
    __table_args__ = (Index("ix_concern_tests_test_id", "test_id"), {"schema": SCHEMA})

    concern_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.health_concerns.id", ondelete="CASCADE"), primary_key=True
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.tests.id", ondelete="CASCADE"), primary_key=True
    )


class ConcernPackage(Base):
    __tablename__ = "concern_packages"
    __table_args__ = (Index("ix_concern_packages_package_id", "package_id"), {"schema": SCHEMA})

    concern_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.health_concerns.id", ondelete="CASCADE"), primary_key=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.packages.id", ondelete="CASCADE"), primary_key=True
    )


class SearchSynonym(TimestampMixin, Base):
    """Everyday or Bangla term → catalog entity ("sugar" → Diabetes, "সুগার" → FBS)."""

    __tablename__ = "search_synonyms"
    __table_args__ = (
        UniqueConstraint("term", "target_type", "target_id", name="uq_search_synonyms_target"),
        CheckConstraint(f"target_type IN {SYNONYM_TARGETS}", name="target_type_valid"),
        CheckConstraint("term = lower(term)", name="term_lowercase"),
        Index("ix_search_synonyms_target", "target_type", "target_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    term: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


Index(
    "ix_search_synonyms_term_trgm",
    SearchSynonym.term,
    postgresql_using="gin",
    postgresql_ops={"term": "gin_trgm_ops"},
)


# ---------------------------------------------------------------- pricing
class PriceList(TimestampMixin, Base):
    """One list per branch; the list with `branch_id IS NULL` is the default."""

    __tablename__ = "price_lists"
    __table_args__ = (
        UniqueConstraint(
            "branch_id", name="uq_price_lists_branch_id", postgresql_nulls_not_distinct=True
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("centre.branches.id", ondelete="RESTRICT")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class PriceListItem(Base):
    """A price valid over [effective_from, effective_to). Rows are closed, never rewritten,
    so price history is kept. Money is integer poisha."""

    __tablename__ = "price_list_items"
    __table_args__ = (
        CheckConstraint(f"item_type IN {ITEM_TYPES}", name="item_type_valid"),
        CheckConstraint(
            "(item_type = 'TEST' AND test_id IS NOT NULL AND package_id IS NULL) OR "
            "(item_type = 'PACKAGE' AND package_id IS NOT NULL AND test_id IS NULL)",
            name="item_ref_matches_type",
        ),
        CheckConstraint("price >= 0 AND mrp >= 0 AND price <= mrp", name="amounts_valid"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="effective_window"
        ),
        Index("ix_price_list_items_test", "price_list_id", "test_id", "effective_from"),
        Index("ix_price_list_items_package", "price_list_id", "package_id", "effective_from"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    price_list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.price_lists.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(10), nullable=False)
    test_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.tests.id", ondelete="RESTRICT")
    )
    package_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.packages.id", ondelete="RESTRICT")
    )
    mrp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
