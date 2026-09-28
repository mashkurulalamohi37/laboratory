"""Published CMS content (public) and content administration (console)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.http import IfMatch, public_cache
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import require
from app.modules.auth.permissions import P
from app.modules.auth.principal import Principal
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
    Placement,
)
from app.modules.cms.service import CmsAdminService, CmsService

router = APIRouter(prefix="/cms", tags=["public: content"])
admin_router = APIRouter(prefix="/admin/cms", tags=["admin: content"])

Db = Annotated[AsyncSession, Depends(get_session)]
Editor = Annotated[Principal, Depends(require(P.CMS_MANAGE))]
_ERR = error_responses(400, 401, 403, 404, 409, 422)
NO_CONTENT = status.HTTP_204_NO_CONTENT


def _svc(db: AsyncSession, actor: Principal) -> CmsAdminService:
    return CmsAdminService(db, actor.user_id, actor.role_codes)


@router.get("/banners", summary="Published banners for a placement")
async def banners(
    db: Db, response: Response, placement: Placement = "HOME_HERO"
) -> Envelope[list[BannerOut]]:
    public_cache(response)
    return ok(await CmsService(db).banners(placement))


@router.get("/pages/{slug}", summary="A published page", responses=error_responses(404))
async def page(slug: str, db: Db, response: Response) -> Envelope[PageOut]:
    public_cache(response, 300)
    return ok(await CmsService(db).page(slug))


@router.get("/faqs", summary="Published FAQs")
async def faqs(
    db: Db,
    response: Response,
    category: Annotated[str | None, Query(max_length=40)] = None,
) -> Envelope[list[FaqOut]]:
    public_cache(response, 300)
    return ok(await CmsService(db).faqs(category))


# ---------------------------------------------------------------- admin
@admin_router.get("/banners", summary="List banners", responses=_ERR)
async def list_banners(actor: Editor, db: Db) -> Envelope[list[AdminBannerOut]]:
    return ok(await _svc(db, actor).list_banners())


@admin_router.post("/banners", status_code=201, summary="Create a banner", responses=_ERR)
async def create_banner(body: BannerIn, actor: Editor, db: Db) -> Envelope[AdminBannerOut]:
    return ok(await _svc(db, actor).create_banner(body))


@admin_router.put("/banners/{obj_id}", summary="Replace a banner", responses=_ERR)
async def replace_banner(
    obj_id: uuid.UUID, body: BannerIn, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminBannerOut]:
    return ok(await _svc(db, actor).replace_banner(obj_id, body, if_match))


@admin_router.delete(
    "/banners/{obj_id}", status_code=NO_CONTENT, summary="Delete a banner", responses=_ERR
)
async def delete_banner(obj_id: uuid.UUID, actor: Editor, db: Db) -> Response:
    await _svc(db, actor).delete_banner(obj_id)
    return Response(status_code=NO_CONTENT)


@admin_router.get("/pages", summary="List pages", responses=_ERR)
async def list_pages(actor: Editor, db: Db) -> Envelope[list[AdminPageOut]]:
    return ok(await _svc(db, actor).list_pages())


@admin_router.post("/pages", status_code=201, summary="Create a page", responses=_ERR)
async def create_page(body: PageIn, actor: Editor, db: Db) -> Envelope[AdminPageOut]:
    return ok(await _svc(db, actor).create_page(body))


@admin_router.put("/pages/{obj_id}", summary="Replace a page", responses=_ERR)
async def replace_page(
    obj_id: uuid.UUID, body: PageIn, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminPageOut]:
    return ok(await _svc(db, actor).replace_page(obj_id, body, if_match))


@admin_router.delete(
    "/pages/{obj_id}", status_code=NO_CONTENT, summary="Delete a page", responses=_ERR
)
async def delete_page(obj_id: uuid.UUID, actor: Editor, db: Db) -> Response:
    await _svc(db, actor).delete_page(obj_id)
    return Response(status_code=NO_CONTENT)


@admin_router.get("/faqs", summary="List FAQs", responses=_ERR)
async def list_faqs(actor: Editor, db: Db) -> Envelope[list[AdminFaqOut]]:
    return ok(await _svc(db, actor).list_faqs())


@admin_router.post("/faqs", status_code=201, summary="Create an FAQ", responses=_ERR)
async def create_faq(body: FaqIn, actor: Editor, db: Db) -> Envelope[AdminFaqOut]:
    return ok(await _svc(db, actor).create_faq(body))


@admin_router.put("/faqs/{obj_id}", summary="Replace an FAQ", responses=_ERR)
async def replace_faq(
    obj_id: uuid.UUID, body: FaqIn, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminFaqOut]:
    return ok(await _svc(db, actor).replace_faq(obj_id, body, if_match))


@admin_router.delete(
    "/faqs/{obj_id}", status_code=NO_CONTENT, summary="Delete an FAQ", responses=_ERR
)
async def delete_faq(obj_id: uuid.UUID, actor: Editor, db: Db) -> Response:
    await _svc(db, actor).delete_faq(obj_id)
    return Response(status_code=NO_CONTENT)
