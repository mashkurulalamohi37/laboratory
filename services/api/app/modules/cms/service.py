"""Public API of the CMS module: published content for the web, and content admin.

Content is visible when `status = PUBLISHED` and `publish_at` (if set) has passed; banners
also hide after `unpublish_at`. Admin edits replace the whole record (PUT semantics) with
optimistic locking.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import SEARCH_NAMESPACE, bump_namespace
from app.core.db import Base, on_commit
from app.core.errors import NotFound
from app.core.sql import check_version, integrity_to_app_error
from app.modules.audit import service as audit
from app.modules.cms.models import Banner, Faq, Page
from app.modules.cms.schemas import (
    AdminBannerOut,
    AdminFaqOut,
    AdminPageOut,
    BannerIn,
    BannerOut,
    FaqIn,
    FaqOut,
    PageIn,
    PageOut,
)

M = TypeVar("M", bound=Base)
Out = TypeVar("Out", bound=BaseModel)


def _published(model: Any) -> list[ColumnElement[bool]]:
    now = func.now()
    conds = [
        model.status == "PUBLISHED",
        or_(model.publish_at.is_(None), model.publish_at <= now),
    ]
    if model is Banner:
        conds.append(or_(Banner.unpublish_at.is_(None), Banner.unpublish_at > now))
    return conds


class CmsService:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def banners(self, placement: str) -> list[BannerOut]:
        rows = await self.s.scalars(
            select(Banner)
            .where(Banner.placement == placement, *_published(Banner))
            .order_by(Banner.sort_order, Banner.created_at)
        )
        return [BannerOut.model_validate(b) for b in rows]

    async def page(self, slug: str) -> PageOut:
        page = await self.s.scalar(select(Page).where(Page.slug == slug, *_published(Page)))
        if page is None:
            raise NotFound()
        return PageOut.model_validate(page)

    async def faqs(self, category: str | None) -> list[FaqOut]:
        stmt = select(Faq).where(*_published(Faq))
        if category:
            stmt = stmt.where(Faq.category == category)
        rows = await self.s.scalars(stmt.order_by(Faq.category, Faq.sort_order, Faq.created_at))
        return [FaqOut.model_validate(f) for f in rows]

    async def sitemap_entries(self) -> list[tuple[str, datetime]]:
        rows = await self.s.execute(select(Page.slug, Page.updated_at).where(*_published(Page)))
        return [(slug, updated) for slug, updated in rows]


class CmsAdminService:
    def __init__(self, session: AsyncSession, actor_id: uuid.UUID, actor_roles: list[str]) -> None:
        self.s = session
        self.actor_id = actor_id
        self.actor_roles = actor_roles
        self._invalidation_queued = False

    def _audit(
        self,
        action: str,
        entity: str,
        entity_id: object,
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
    ) -> None:
        audit.record(
            self.s,
            action=action,
            entity_type=entity,
            entity_id=str(entity_id),
            actor_user_id=self.actor_id,
            actor_roles=self.actor_roles,
            before=before,
            after=after,
        )
        if not self._invalidation_queued:  # the sitemap lists published pages
            on_commit(self.s, lambda: bump_namespace(SEARCH_NAMESPACE))
            self._invalidation_queued = True

    async def _flush(self) -> None:
        try:
            await self.s.flush()
        except IntegrityError as exc:
            raise integrity_to_app_error(exc, duplicate="This slug is already used.") from exc

    async def _list(self, model: type[M], out: type[Out], *order: Any) -> list[Out]:
        rows = await self.s.scalars(select(model).order_by(*order))
        return [out.model_validate(r) for r in rows]

    async def _create(self, model: type[M], body: BaseModel, out: type[Out], entity: str) -> Out:
        obj: Any = model(**body.model_dump())
        self.s.add(obj)
        await self._flush()
        await self.s.refresh(obj)
        self._audit(f"{entity}.created", entity, obj.id, after=body.model_dump(mode="json"))
        return out.model_validate(obj)

    async def _replace(
        self,
        model: type[M],
        obj_id: uuid.UUID,
        body: BaseModel,
        if_match: int | None,
        out: type[Out],
        entity: str,
    ) -> Out:
        obj: Any = await self.s.get(model, obj_id, with_for_update=True)
        if obj is None:
            raise NotFound()
        check_version(obj.version, if_match)
        data = body.model_dump()
        before = {k: getattr(obj, k) for k in data}
        for k, v in data.items():
            setattr(obj, k, v)
        obj.version += 1
        await self._flush()
        await self.s.refresh(obj)
        self._audit(
            f"{entity}.updated",
            entity,
            obj.id,
            before=before,
            after=body.model_dump(mode="json"),
        )
        return out.model_validate(obj)

    async def _delete(self, model: type[M], obj_id: uuid.UUID, entity: str) -> None:
        obj: Any = await self.s.get(model, obj_id)
        if obj is None:
            raise NotFound()
        self._audit(f"{entity}.deleted", entity, obj.id, before={"status": obj.status})
        await self.s.delete(obj)

    # banners
    async def list_banners(self) -> list[AdminBannerOut]:
        return await self._list(Banner, AdminBannerOut, Banner.placement, Banner.sort_order)

    async def create_banner(self, body: BannerIn) -> AdminBannerOut:
        return await self._create(Banner, body, AdminBannerOut, "banner")

    async def replace_banner(
        self, obj_id: uuid.UUID, body: BannerIn, if_match: int | None
    ) -> AdminBannerOut:
        return await self._replace(Banner, obj_id, body, if_match, AdminBannerOut, "banner")

    async def delete_banner(self, obj_id: uuid.UUID) -> None:
        await self._delete(Banner, obj_id, "banner")

    # pages
    async def list_pages(self) -> list[AdminPageOut]:
        return await self._list(Page, AdminPageOut, Page.slug)

    async def create_page(self, body: PageIn) -> AdminPageOut:
        return await self._create(Page, body, AdminPageOut, "page")

    async def replace_page(
        self, obj_id: uuid.UUID, body: PageIn, if_match: int | None
    ) -> AdminPageOut:
        return await self._replace(Page, obj_id, body, if_match, AdminPageOut, "page")

    async def delete_page(self, obj_id: uuid.UUID) -> None:
        await self._delete(Page, obj_id, "page")

    # FAQs
    async def list_faqs(self) -> list[AdminFaqOut]:
        return await self._list(Faq, AdminFaqOut, Faq.category, Faq.sort_order)

    async def create_faq(self, body: FaqIn) -> AdminFaqOut:
        return await self._create(Faq, body, AdminFaqOut, "faq")

    async def replace_faq(
        self, obj_id: uuid.UUID, body: FaqIn, if_match: int | None
    ) -> AdminFaqOut:
        return await self._replace(Faq, obj_id, body, if_match, AdminFaqOut, "faq")

    async def delete_faq(self, obj_id: uuid.UUID) -> None:
        await self._delete(Faq, obj_id, "faq")
