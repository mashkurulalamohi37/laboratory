"""Database repository for result and critical alert records."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.result.models import CriticalAlert, Result


class ResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current_result(self, lab_order_item_id: uuid.UUID) -> Result | None:
        stmt = (
            select(Result)
            .options(selectinload(Result.parameters), selectinload(Result.comments))
            .where(Result.lab_order_item_id == lab_order_item_id)
            .where(Result.is_current.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_result_by_id(self, result_id: uuid.UUID) -> Result | None:
        stmt = (
            select(Result)
            .options(selectinload(Result.parameters), selectinload(Result.comments))
            .where(Result.id == result_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_result(self, result_obj: Result) -> Result:
        self._session.add(result_obj)
        await self._session.flush()
        return result_obj

    async def save_alert(self, alert: CriticalAlert) -> CriticalAlert:
        self._session.add(alert)
        await self._session.flush()
        return alert

    async def get_alert_by_id(self, alert_id: uuid.UUID) -> CriticalAlert | None:
        stmt = select(CriticalAlert).where(CriticalAlert.id == alert_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_critical_alerts(self, status: str | None = None) -> Sequence[CriticalAlert]:
        stmt = select(CriticalAlert).order_by(CriticalAlert.created_at.desc())
        if status:
            stmt = stmt.where(CriticalAlert.status == status)
        result = await self._session.execute(stmt)
        return result.scalars().all()
