"""Cross-entity search and the SEO sitemap feed.

Autocomplete is read-through cached in Redis under the `search` namespace, which catalog
and centre changes bump after commit, so edits show up immediately without a TTL wait.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import SEARCH_NAMESPACE, cached_json
from app.core.text import normalize_query
from app.modules.catalog.schemas import (
    ConcernSummary,
    PackageSummary,
    SitemapEntry,
    Suggestion,
    TestSummary,
)
from app.modules.catalog.service import CatalogService
from app.modules.centre.schemas import CentreSummary
from app.modules.centre.service import CentreService
from app.modules.cms.service import CmsService

SearchType = Literal["test", "package", "concern", "centre"]
ALL_TYPES: frozenset[str] = frozenset({"test", "package", "concern", "centre"})

AUTOCOMPLETE_TTL = 300
SITEMAP_TTL = 600


class SearchResults(BaseModel):
    query: str
    tests: list[TestSummary]
    packages: list[PackageSummary]
    concerns: list[ConcernSummary]
    centres: list[CentreSummary]

    @property
    def total(self) -> int:
        return len(self.tests) + len(self.packages) + len(self.concerns) + len(self.centres)


async def search(session: AsyncSession, q: str, *, types: set[str], limit: int) -> SearchResults:
    normalized = normalize_query(q)
    catalog = await CatalogService.create(session)
    hits = await catalog.search(normalized, limit=limit, types=types)
    centres = (
        await CentreService(session).search(normalized, limit)
        if "centre" in types and normalized
        else []
    )
    return SearchResults(
        query=normalized,
        tests=hits.tests,
        packages=hits.packages,
        concerns=hits.concerns,
        centres=centres,
    )


async def autocomplete(session: AsyncSession, q: str) -> list[Suggestion]:
    normalized = normalize_query(q)
    if len(normalized) < 2:
        return []

    async def compute() -> list[dict[str, Any]]:
        results = await search(session, normalized, types=set(ALL_TYPES), limit=5)
        out: list[Suggestion] = []
        out += [
            Suggestion(type="concern", slug=c.slug, name=c.name, name_bn=c.name_bn)
            for c in results.concerns[:2]
        ]
        out += [
            Suggestion(type="test", slug=t.slug, name=t.name, name_bn=t.name_bn, price=t.price)
            for t in results.tests[:5]
        ]
        out += [
            Suggestion(type="package", slug=p.slug, name=p.name, name_bn=p.name_bn, price=p.price)
            for p in results.packages[:3]
        ]
        out += [
            Suggestion(type="centre", slug=c.slug, name=c.name, name_bn=c.name_bn)
            for c in results.centres[:2]
        ]
        return [s.model_dump(mode="json") for s in out]

    rows = await cached_json(SEARCH_NAMESPACE, f"ac:{normalized}", AUTOCOMPLETE_TTL, compute)
    return [Suggestion.model_validate(r) for r in rows]


async def sitemap(session: AsyncSession) -> list[SitemapEntry]:
    async def compute() -> list[dict[str, Any]]:
        entries: list[SitemapEntry] = []
        catalog = await CatalogService.create(session)
        for kind, slug, updated in await catalog.sitemap_entries():
            entries.append(SitemapEntry(type=kind, slug=slug, updated_at=updated))
        for slug, updated in await CentreService(session).sitemap_entries():
            entries.append(SitemapEntry(type="centre", slug=slug, updated_at=updated))
        for slug, updated in await CmsService(session).sitemap_entries():
            entries.append(SitemapEntry(type="page", slug=slug, updated_at=updated))
        return [e.model_dump(mode="json") for e in entries]

    rows = await cached_json(SEARCH_NAMESPACE, "sitemap", SITEMAP_TTL, compute)
    return [SitemapEntry.model_validate(r) for r in rows]
