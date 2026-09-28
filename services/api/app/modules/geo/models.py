"""Bangladesh administrative geography: division → district → upazila/thana → area.

Reference data (seeded, rarely edited). Names are stored in English and Bangla.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "geo"


class _Named:
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_bn: Mapped[str] = mapped_column(String(120), nullable=False)


class Division(_Named, TimestampMixin, Base):
    __tablename__ = "divisions"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUIDPk]


class District(_Named, TimestampMixin, Base):
    __tablename__ = "districts"
    __table_args__ = (Index("ix_districts_division_id", "division_id"), {"schema": SCHEMA})

    id: Mapped[UUIDPk]
    division_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.divisions.id", ondelete="RESTRICT"), nullable=False
    )


class Upazila(_Named, TimestampMixin, Base):
    __tablename__ = "upazilas"
    __table_args__ = (Index("ix_upazilas_district_id", "district_id"), {"schema": SCHEMA})

    id: Mapped[UUIDPk]
    district_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.districts.id", ondelete="RESTRICT"), nullable=False
    )


class Area(_Named, TimestampMixin, Base):
    __tablename__ = "areas"
    __table_args__ = (Index("ix_areas_upazila_id", "upazila_id"), {"schema": SCHEMA})

    id: Mapped[UUIDPk]
    upazila_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.upazilas.id", ondelete="RESTRICT"), nullable=False
    )
    postcode: Mapped[str | None] = mapped_column(String(8))
