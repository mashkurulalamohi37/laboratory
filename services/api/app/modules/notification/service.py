"""Business logic for notification template configuration and dispatch tracking."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.notification.models import NotificationLog, NotificationTemplate
from app.modules.notification.schemas import NotificationTemplateCreate


class NotificationManagementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_template(
        self, data: NotificationTemplateCreate
    ) -> NotificationTemplate:
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.code == data.code,
            NotificationTemplate.channel == data.channel,
            NotificationTemplate.language == data.language,
        )
        res = await self.session.execute(stmt)
        template = res.scalar_one_or_none()

        if template:
            template.title = data.title
            template.body_template = data.body_template
            template.is_active = data.is_active
        else:
            template = NotificationTemplate(
                id=uuid7(),
                code=data.code,
                channel=data.channel,
                language=data.language,
                title=data.title,
                body_template=data.body_template,
                is_active=data.is_active,
            )
            self.session.add(template)

        await self.session.commit()
        return template

    async def list_templates(
        self, channel: str | None = None
    ) -> Sequence[NotificationTemplate]:
        stmt = select(NotificationTemplate).order_by(NotificationTemplate.code)
        if channel:
            stmt = stmt.where(NotificationTemplate.channel == channel)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def log_dispatch(
        self,
        recipient: str,
        channel: str,
        template_code: str,
        status: str = "SENT",
        error_message: str | None = None,
    ) -> NotificationLog:
        log = NotificationLog(
            id=uuid7(),
            recipient=recipient,
            channel=channel,
            template_code=template_code,
            status=status,
            error_message=error_message,
        )
        self.session.add(log)
        await self.session.commit()
        return log

    async def list_history(
        self, channel: str | None = None, limit: int = 100
    ) -> Sequence[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .order_by(desc(NotificationLog.dispatched_at))
            .limit(limit)
        )
        if channel:
            stmt = stmt.where(NotificationLog.channel == channel)
        res = await self.session.execute(stmt)
        return res.scalars().all()
