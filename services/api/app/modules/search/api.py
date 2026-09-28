"""Public search, autocomplete and the sitemap feed used by the web prerenderer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import ErrorDetail, ValidationFailed, error_responses
from app.core.http import public_cache
from app.core.responses import Envelope, ok
from app.modules.catalog.schemas import SitemapEntry, Suggestion
from app.modules.search import service
from app.modules.search.service import ALL_TYPES, SearchResults

router = APIRouter(tags=["public: search"])

Db = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/search",
    summary="Search tests, packages, health concerns and centres",
    description="Full-text prefix matching, trigram typo tolerance and synonyms "
    '(everyday and Bangla terms, e.g. "sugar" → glucose tests).',
    responses=error_responses(400),
)
async def search(
    db: Db,
    response: Response,
    q: Annotated[str, Query(min_length=1, max_length=80)],
    types: Annotated[
        str, Query(description="Comma-separated subset of: test,package,concern,centre")
    ] = "test,package,concern,centre",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> Envelope[SearchResults]:
    wanted = {t.strip() for t in types.split(",") if t.strip()}
    if not wanted or not wanted <= ALL_TYPES:
        raise ValidationFailed(
            details=[ErrorDetail(field="types", issue=f"allowed: {', '.join(sorted(ALL_TYPES))}")]
        )
    public_cache(response)
    return ok(await service.search(db, q, types=wanted, limit=limit))


@router.get(
    "/search/autocomplete",
    summary="Search suggestions while typing",
    description="Cached; at most 12 suggestions grouped by type.",
    responses=error_responses(400),
)
async def autocomplete(
    db: Db, response: Response, q: Annotated[str, Query(max_length=80)]
) -> Envelope[list[Suggestion]]:
    public_cache(response)
    return ok(await service.autocomplete(db, q))


@router.get("/seo/sitemap", summary="Public URLs for the sitemap")
async def sitemap(db: Db, response: Response) -> Envelope[list[SitemapEntry]]:
    public_cache(response, 600)
    return ok(await service.sitemap(db))
