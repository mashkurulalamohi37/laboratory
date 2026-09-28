"""Repository for report queries and persistence."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.report.models import (
    Report,
    ReportShare,
    ReportVerificationToken,
    ReportVersion,
)


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, report_id: uuid.UUID) -> Report | None:
        stmt = (
            select(Report)
            .where(Report.id == report_id)
            .options(
                selectinload(Report.versions).selectinload(ReportVersion.signatures),
                selectinload(Report.versions).selectinload(ReportVersion.verification_token),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, report_code: str) -> Report | None:
        stmt = (
            select(Report)
            .where(Report.report_code == report_code)
            .options(
                selectinload(Report.versions).selectinload(ReportVersion.signatures),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_lab_order(self, lab_order_id: uuid.UUID) -> Report | None:
        stmt = (
            select(Report)
            .where(Report.lab_order_id == lab_order_id)
            .options(
                selectinload(Report.versions).selectinload(ReportVersion.signatures),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_patient(self, patient_id: uuid.UUID) -> Sequence[Report]:
        stmt = (
            select(Report)
            .where(Report.patient_id == patient_id)
            .options(
                selectinload(Report.versions).selectinload(ReportVersion.signatures),
            )
            .order_by(desc(Report.created_at))
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_version(self, version_id: uuid.UUID) -> ReportVersion | None:
        stmt = (
            select(ReportVersion)
            .where(ReportVersion.id == version_id)
            .options(
                selectinload(ReportVersion.signatures),
                selectinload(ReportVersion.verification_token),
                selectinload(ReportVersion.report),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> ReportVerificationToken | None:
        stmt = (
            select(ReportVerificationToken)
            .where(
                ReportVerificationToken.token == token,
                ReportVerificationToken.is_active.is_(True),
            )
            .options(
                selectinload(ReportVerificationToken.version).selectinload(ReportVersion.report),
                selectinload(ReportVerificationToken.version).selectinload(ReportVersion.signatures),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_share(self, share_token: str) -> ReportShare | None:
        stmt = select(ReportShare).where(ReportShare.share_token == share_token)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
