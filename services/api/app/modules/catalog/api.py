"""Public catalog: tests, packages, health concerns and filter facets."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.http import public_cache
from app.core.responses import Envelope, ok
from app.modules.catalog.schemas import (
    CatalogFilters,
    ConcernDetail,
    ConcernSummary,
    PackageDetail,
    PackageSummary,
    Sex,
    TestDetail,
    TestSummary,
)
from app.modules.catalog.service import (
    CatalogService,
    PackageFilters,
    PackageSort,
    TestFilters,
    TestSort,
)

router = APIRouter(tags=["public: catalog"])

Db = Annotated[AsyncSession, Depends(get_session)]
BranchId = Annotated[
    uuid.UUID | None,
    Query(description="Price with this branch's list (falls back to the default list)"),
]
PageNo = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Poisha = Annotated[int | None, Query(ge=0, description="Poisha (1/100 BDT)")]


@router.get("/catalog/filters", summary="Filter facets for the test list")
async def catalog_filters(db: Db, response: Response) -> Envelope[CatalogFilters]:
    public_cache(response, 300)
    return ok(await (await CatalogService.create(db)).filters())


@router.get(
    "/tests",
    summary="List tests",
    description="Public test catalogue with filters. Prices come from the branch price list "
    "when `branch_id` is given, otherwise from the default list.",
    responses=error_responses(400),
)
async def list_tests(
    db: Db,
    response: Response,
    q: Annotated[str | None, Query(max_length=80)] = None,
    department: Annotated[str | None, Query(max_length=40, description="Department code")] = None,
    category: Annotated[str | None, Query(max_length=120, description="Category slug")] = None,
    sample_type: Annotated[str | None, Query(max_length=40, description="Sample type code")] = None,
    concern: Annotated[str | None, Query(max_length=120, description="Concern slug")] = None,
    home_collection: bool | None = None,
    tat_max: Annotated[int | None, Query(ge=1, description="Maximum turnaround, hours")] = None,
    price_min: Poisha = None,
    price_max: Poisha = None,
    featured: bool | None = None,
    sort: TestSort = "popular",
    branch_id: BranchId = None,
    page: PageNo = 1,
    page_size: PageSize = 20,
) -> Envelope[list[TestSummary]]:
    public_cache(response)
    service = await CatalogService.create(db, branch_id)
    items, total = await service.list_tests(
        TestFilters(
            q=q,
            department=department,
            category=category,
            sample_type=sample_type,
            concern=concern,
            home_collection=home_collection,
            tat_max=tat_max,
            price_min=price_min,
            price_max=price_max,
            featured=featured,
        ),
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ok(items, page=page, page_size=page_size, total=total)


@router.get("/tests/{slug}", summary="Test details", responses=error_responses(404))
async def get_test(
    slug: str, db: Db, response: Response, branch_id: BranchId = None
) -> Envelope[TestDetail]:
    public_cache(response)
    return ok(await (await CatalogService.create(db, branch_id)).get_test(slug))


@router.get("/packages", summary="List health packages", responses=error_responses(400))
async def list_packages(
    db: Db,
    response: Response,
    q: Annotated[str | None, Query(max_length=80)] = None,
    sex: Annotated[Sex | None, Query(description="Show packages suitable for this sex")] = None,
    age: Annotated[int | None, Query(ge=0, le=120, description="Age in years")] = None,
    concern: Annotated[str | None, Query(max_length=120)] = None,
    price_min: Poisha = None,
    price_max: Poisha = None,
    featured: bool | None = None,
    sort: PackageSort = "popular",
    branch_id: BranchId = None,
    page: PageNo = 1,
    page_size: PageSize = 20,
) -> Envelope[list[PackageSummary]]:
    public_cache(response)
    service = await CatalogService.create(db, branch_id)
    items, total = await service.list_packages(
        PackageFilters(
            q=q,
            sex=sex,
            age=age,
            concern=concern,
            price_min=price_min,
            price_max=price_max,
            featured=featured,
        ),
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ok(items, page=page, page_size=page_size, total=total)


@router.get("/packages/{slug}", summary="Package details", responses=error_responses(404))
async def get_package(
    slug: str, db: Db, response: Response, branch_id: BranchId = None
) -> Envelope[PackageDetail]:
    public_cache(response)
    return ok(await (await CatalogService.create(db, branch_id)).get_package(slug))


@router.get("/health-concerns", summary="List health concerns")
async def list_concerns(
    db: Db, response: Response, featured: bool | None = None
) -> Envelope[list[ConcernSummary]]:
    public_cache(response, 300)
    return ok(await (await CatalogService.create(db)).list_concerns(featured=featured))


@router.get(
    "/health-concerns/{slug}",
    summary="Health concern with its tests and packages",
    responses=error_responses(404),
)
async def get_concern(
    slug: str, db: Db, response: Response, branch_id: BranchId = None
) -> Envelope[ConcernDetail]:
    public_cache(response)
    return ok(await (await CatalogService.create(db, branch_id)).get_concern(slug))
