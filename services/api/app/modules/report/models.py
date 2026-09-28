"""SQLAlchemy models for medical diagnostic reports, versions, signatures, and verification."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk


class Report(Base, TimestampMixin):
    """Primary clinical diagnostic report document."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("report_code", name="uq_reports_report_code"),
        Index("ix_reports_patient_id", "patient_id"),
        Index("ix_reports_lab_order_id", "lab_order_id"),
        {"schema": "report"},
    )

    id: Mapped[UUIDPk]
    report_code: Mapped[str] = mapped_column(String(32), nullable=False)  # REP-YYYY-NNNNNN
    lab_order_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Status: GENERATING, FINAL, SUPERSEDED
    status: Mapped[str] = mapped_column(String(32), default="FINAL", nullable=False)

    versions: Mapped[list[ReportVersion]] = relationship(
        "ReportVersion",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportVersion.version_no.desc()",
    )


class ReportVersion(Base, TimestampMixin):
    """Immutable version of a generated diagnostic report."""

    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint("report_id", "version_no", name="uq_report_versions_version_no"),
        Index("ix_report_versions_report_id", "report_id"),
        {"schema": "report"},
    )

    id: Mapped[UUIDPk]
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("report.reports.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Status: FINAL, SUPERSEDED
    status: Mapped[str] = mapped_column(String(32), default="FINAL", nullable=False)
    amend_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped[Report] = relationship("Report", back_populates="versions")
    signatures: Mapped[list[ReportSignature]] = relationship(
        "ReportSignature",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    verification_token: Mapped[ReportVerificationToken | None] = relationship(
        "ReportVerificationToken",
        back_populates="version",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ReportSignature(Base, TimestampMixin):
    """Pathologist digital sign-off and certification record."""

    __tablename__ = "report_signatures"
    __table_args__ = (
        Index("ix_report_signatures_version_id", "version_id"),
        {"schema": "report"},
    )

    id: Mapped[UUIDPk]
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("report.report_versions.id", ondelete="CASCADE"), nullable=False
    )
    pathologist_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    pathologist_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Bangladesh Medical & Dental Council reg number
    bmdc_number: Mapped[str] = mapped_column(String(64), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    signature_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    version: Mapped[ReportVersion] = relationship("ReportVersion", back_populates="signatures")


class ReportVerificationToken(Base, TimestampMixin):
    """Public QR verification token linking to authenticated report details."""

    __tablename__ = "report_verification_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_report_verification_tokens_token"),
        Index("ix_report_verification_tokens_version_id", "version_id"),
        {"schema": "report"},
    )

    id: Mapped[UUIDPk]
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("report.report_versions.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    version: Mapped[ReportVersion] = relationship(
        "ReportVersion", back_populates="verification_token"
    )


class ReportShare(Base, TimestampMixin):
    """Time-limited shareable access token for patients to share reports with external doctors."""

    __tablename__ = "report_shares"
    __table_args__ = (
        UniqueConstraint("share_token", name="uq_report_shares_share_token"),
        Index("ix_report_shares_report_id", "report_id"),
        {"schema": "report"},
    )

    id: Mapped[UUIDPk]
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("report.reports.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    share_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
