"""Console endpoints for catalog administration."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.http import IfMatch
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import require
from app.modules.auth.permissions import P
from app.modules.auth.principal import Principal
from app.modules.catalog.admin_service import CatalogAdminService
from app.modules.catalog.schemas import (
    AdminCategoryOut,
    AdminConcernOut,
    AdminDepartmentOut,
    AdminPackageListItem,
    AdminPackageOut,
    AdminPreparationOut,
    AdminSampleTypeOut,
    AdminTestListItem,
    AdminTestOut,
    CategoryIn,
    CategoryUpdate,
    ConcernIn,
    ConcernUpdate,
    DepartmentIn,
    DepartmentUpdate,
    ItemType,
    PackageIn,
    PackageUpdate,
    ParameterIn,
    ParameterUpdate,
    PreparationIn,
    PreparationUpdate,
    PriceHistoryOut,
    PriceItemOut,
    PriceListIn,
    PriceListOut,
    PriceListUpdate,
    ReferenceRangeIn,
    SampleTypeIn,
    SampleTypeUpdate,
    SetPriceIn,
    SynonymIn,
    SynonymOut,
    SynonymTarget,
    TestIn,
    TestUpdate,
)

router = APIRouter(prefix="/admin/catalog", tags=["admin: catalog"])

Db = Annotated[AsyncSession, Depends(get_session)]
Viewer = Annotated[Principal, Depends(require(P.TEST_VIEW))]
Creator = Annotated[Principal, Depends(require(P.TEST_CREATE))]
Editor = Annotated[Principal, Depends(require(P.TEST_UPDATE))]
Deleter = Annotated[Principal, Depends(require(P.TEST_DELETE))]
PackageManager = Annotated[Principal, Depends(require(P.PACKAGE_MANAGE))]
PriceManager = Annotated[Principal, Depends(require(P.PRICE_MANAGE))]
PriceViewer = Annotated[Principal, Depends(require(P.TEST_VIEW, P.PRICE_MANAGE, any_of=True))]
_ERR = error_responses(400, 401, 403, 404, 409, 422)
NO_CONTENT = status.HTTP_204_NO_CONTENT


def _svc(db: AsyncSession, actor: Principal) -> CatalogAdminService:
    return CatalogAdminService(db, actor.user_id, actor.role_codes)


# ---------------------------------------------------------------- master data
@router.get("/departments", summary="List departments", responses=_ERR)
async def list_departments(actor: Viewer, db: Db) -> Envelope[list[AdminDepartmentOut]]:
    return ok(await _svc(db, actor).list_departments())


@router.post("/departments", status_code=201, summary="Create a department", responses=_ERR)
async def create_department(
    body: DepartmentIn, actor: Creator, db: Db
) -> Envelope[AdminDepartmentOut]:
    return ok(await _svc(db, actor).create_department(body))


@router.patch("/departments/{obj_id}", summary="Update a department", responses=_ERR)
async def update_department(
    obj_id: uuid.UUID, body: DepartmentUpdate, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminDepartmentOut]:
    return ok(await _svc(db, actor).update_department(obj_id, body, if_match))


@router.get("/categories", summary="List categories", responses=_ERR)
async def list_categories(actor: Viewer, db: Db) -> Envelope[list[AdminCategoryOut]]:
    return ok(await _svc(db, actor).list_categories())


@router.post("/categories", status_code=201, summary="Create a category", responses=_ERR)
async def create_category(body: CategoryIn, actor: Creator, db: Db) -> Envelope[AdminCategoryOut]:
    return ok(await _svc(db, actor).create_category(body))


@router.patch("/categories/{obj_id}", summary="Update a category", responses=_ERR)
async def update_category(
    obj_id: uuid.UUID, body: CategoryUpdate, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminCategoryOut]:
    return ok(await _svc(db, actor).update_category(obj_id, body, if_match))


@router.get("/sample-types", summary="List sample types", responses=_ERR)
async def list_sample_types(actor: Viewer, db: Db) -> Envelope[list[AdminSampleTypeOut]]:
    return ok(await _svc(db, actor).list_sample_types())


@router.post("/sample-types", status_code=201, summary="Create a sample type", responses=_ERR)
async def create_sample_type(
    body: SampleTypeIn, actor: Creator, db: Db
) -> Envelope[AdminSampleTypeOut]:
    return ok(await _svc(db, actor).create_sample_type(body))


@router.patch("/sample-types/{obj_id}", summary="Update a sample type", responses=_ERR)
async def update_sample_type(
    obj_id: uuid.UUID, body: SampleTypeUpdate, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminSampleTypeOut]:
    return ok(await _svc(db, actor).update_sample_type(obj_id, body, if_match))


@router.get("/preparations", summary="List preparation instructions", responses=_ERR)
async def list_preparations(actor: Viewer, db: Db) -> Envelope[list[AdminPreparationOut]]:
    return ok(await _svc(db, actor).list_preparations())


@router.post("/preparations", status_code=201, summary="Create a preparation", responses=_ERR)
async def create_preparation(
    body: PreparationIn, actor: Creator, db: Db
) -> Envelope[AdminPreparationOut]:
    return ok(await _svc(db, actor).create_preparation(body))


@router.patch("/preparations/{obj_id}", summary="Update a preparation", responses=_ERR)
async def update_preparation(
    obj_id: uuid.UUID, body: PreparationUpdate, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminPreparationOut]:
    return ok(await _svc(db, actor).update_preparation(obj_id, body, if_match))


# ---------------------------------------------------------------- tests
@router.get("/tests", summary="List tests (console)", responses=_ERR)
async def list_tests(
    actor: Viewer,
    db: Db,
    q: Annotated[str | None, Query(max_length=80)] = None,
    department_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[list[AdminTestListItem]]:
    items, total = await _svc(db, actor).list_tests(
        q=q, department_id=department_id, is_active=is_active, page=page, page_size=page_size
    )
    return ok(items, page=page, page_size=page_size, total=total)


@router.post("/tests", status_code=201, summary="Create a test", responses=_ERR)
async def create_test(body: TestIn, actor: Creator, db: Db) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).create_test(body))


@router.get("/tests/{test_id}", summary="Get a test with parameters and ranges", responses=_ERR)
async def get_test(test_id: uuid.UUID, actor: Viewer, db: Db) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).get_test(test_id))


@router.patch("/tests/{test_id}", summary="Update a test", responses=_ERR)
async def update_test(
    test_id: uuid.UUID, body: TestUpdate, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).update_test(test_id, body, if_match))


@router.delete(
    "/tests/{test_id}",
    status_code=NO_CONTENT,
    summary="Delete a test (soft)",
    description="Refused while the test belongs to an active package.",
    responses=_ERR,
)
async def delete_test(test_id: uuid.UUID, actor: Deleter, db: Db, if_match: IfMatch) -> Response:
    await _svc(db, actor).delete_test(test_id, if_match)
    return Response(status_code=NO_CONTENT)


@router.post(
    "/tests/{test_id}/parameters", status_code=201, summary="Add a parameter", responses=_ERR
)
async def add_parameter(
    test_id: uuid.UUID, body: ParameterIn, actor: Editor, db: Db
) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).add_parameter(test_id, body))


@router.patch("/parameters/{parameter_id}", summary="Update a parameter", responses=_ERR)
async def update_parameter(
    parameter_id: uuid.UUID, body: ParameterUpdate, actor: Editor, db: Db
) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).update_parameter(parameter_id, body))


@router.delete("/parameters/{parameter_id}", summary="Remove a parameter", responses=_ERR)
async def delete_parameter(
    parameter_id: uuid.UUID, actor: Editor, db: Db
) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).delete_parameter(parameter_id))


@router.post(
    "/parameters/{parameter_id}/reference-ranges",
    status_code=201,
    summary="Add a reference range",
    description="Ranges with identical criteria may not overlap in age band and validity "
    "(409 REFERENCE_RANGE_OVERLAP).",
    responses=_ERR,
)
async def add_range(
    parameter_id: uuid.UUID, body: ReferenceRangeIn, actor: Editor, db: Db
) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).add_range(parameter_id, body))


@router.put("/reference-ranges/{range_id}", summary="Replace a reference range", responses=_ERR)
async def update_range(
    range_id: uuid.UUID, body: ReferenceRangeIn, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).update_range(range_id, body, if_match))


@router.delete("/reference-ranges/{range_id}", summary="Remove a reference range", responses=_ERR)
async def delete_range(range_id: uuid.UUID, actor: Editor, db: Db) -> Envelope[AdminTestOut]:
    return ok(await _svc(db, actor).delete_range(range_id))


# ---------------------------------------------------------------- packages
@router.get("/packages", summary="List packages (console)", responses=_ERR)
async def list_packages(
    actor: Viewer,
    db: Db,
    q: Annotated[str | None, Query(max_length=80)] = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[list[AdminPackageListItem]]:
    items, total = await _svc(db, actor).list_packages(
        q=q, is_active=is_active, page=page, page_size=page_size
    )
    return ok(items, page=page, page_size=page_size, total=total)


@router.post("/packages", status_code=201, summary="Create a package", responses=_ERR)
async def create_package(
    body: PackageIn, actor: PackageManager, db: Db
) -> Envelope[AdminPackageOut]:
    return ok(await _svc(db, actor).create_package(body))


@router.get("/packages/{package_id}", summary="Get a package (console)", responses=_ERR)
async def get_package(package_id: uuid.UUID, actor: Viewer, db: Db) -> Envelope[AdminPackageOut]:
    return ok(await _svc(db, actor).get_package(package_id))


@router.patch(
    "/packages/{package_id}",
    summary="Update a package",
    description="`test_ids`, when present, replaces the package contents (in order).",
    responses=_ERR,
)
async def update_package(
    package_id: uuid.UUID, body: PackageUpdate, actor: PackageManager, db: Db, if_match: IfMatch
) -> Envelope[AdminPackageOut]:
    return ok(await _svc(db, actor).update_package(package_id, body, if_match))


@router.delete(
    "/packages/{package_id}", status_code=NO_CONTENT, summary="Delete a package", responses=_ERR
)
async def delete_package(
    package_id: uuid.UUID, actor: PackageManager, db: Db, if_match: IfMatch
) -> Response:
    await _svc(db, actor).delete_package(package_id, if_match)
    return Response(status_code=NO_CONTENT)


# ---------------------------------------------------------------- concerns & synonyms
@router.get("/health-concerns", summary="List health concerns (console)", responses=_ERR)
async def list_concerns(actor: Viewer, db: Db) -> Envelope[list[AdminConcernOut]]:
    return ok(await _svc(db, actor).list_concerns())


@router.post("/health-concerns", status_code=201, summary="Create a concern", responses=_ERR)
async def create_concern(body: ConcernIn, actor: Editor, db: Db) -> Envelope[AdminConcernOut]:
    return ok(await _svc(db, actor).create_concern(body))


@router.patch("/health-concerns/{concern_id}", summary="Update a concern", responses=_ERR)
async def update_concern(
    concern_id: uuid.UUID, body: ConcernUpdate, actor: Editor, db: Db, if_match: IfMatch
) -> Envelope[AdminConcernOut]:
    return ok(await _svc(db, actor).update_concern(concern_id, body, if_match))


@router.delete(
    "/health-concerns/{concern_id}",
    status_code=NO_CONTENT,
    summary="Delete a concern",
    responses=_ERR,
)
async def delete_concern(
    concern_id: uuid.UUID, actor: Deleter, db: Db, if_match: IfMatch
) -> Response:
    await _svc(db, actor).delete_concern(concern_id, if_match)
    return Response(status_code=NO_CONTENT)


@router.get("/synonyms", summary="List search synonyms", responses=_ERR)
async def list_synonyms(
    actor: Viewer,
    db: Db,
    q: Annotated[str | None, Query(max_length=80)] = None,
    target_type: SynonymTarget | None = None,
    target_id: uuid.UUID | None = None,
) -> Envelope[list[SynonymOut]]:
    return ok(
        await _svc(db, actor).list_synonyms(q=q, target_type=target_type, target_id=target_id)
    )


@router.post("/synonyms", status_code=201, summary="Add a search synonym", responses=_ERR)
async def create_synonym(body: SynonymIn, actor: Editor, db: Db) -> Envelope[SynonymOut]:
    return ok(await _svc(db, actor).create_synonym(body))


@router.delete(
    "/synonyms/{synonym_id}", status_code=NO_CONTENT, summary="Remove a synonym", responses=_ERR
)
async def delete_synonym(synonym_id: uuid.UUID, actor: Editor, db: Db) -> Response:
    await _svc(db, actor).delete_synonym(synonym_id)
    return Response(status_code=NO_CONTENT)


# ---------------------------------------------------------------- price lists
@router.get("/price-lists", summary="List price lists", responses=_ERR)
async def list_price_lists(actor: PriceViewer, db: Db) -> Envelope[list[PriceListOut]]:
    return ok(await _svc(db, actor).list_price_lists())


@router.post("/price-lists", status_code=201, summary="Create a price list", responses=_ERR)
async def create_price_list(
    body: PriceListIn, actor: PriceManager, db: Db
) -> Envelope[PriceListOut]:
    return ok(await _svc(db, actor).create_price_list(body))


@router.patch("/price-lists/{price_list_id}", summary="Update a price list", responses=_ERR)
async def update_price_list(
    price_list_id: uuid.UUID,
    body: PriceListUpdate,
    actor: PriceManager,
    db: Db,
    if_match: IfMatch,
) -> Envelope[PriceListOut]:
    return ok(await _svc(db, actor).update_price_list(price_list_id, body, if_match))


@router.get(
    "/price-lists/{price_list_id}/items",
    summary="Prices of tests or packages in a list",
    responses=_ERR,
)
async def list_price_items(
    price_list_id: uuid.UUID,
    actor: PriceViewer,
    db: Db,
    item_type: ItemType = "TEST",
    q: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Envelope[list[PriceItemOut]]:
    items, total = await _svc(db, actor).list_price_items(
        price_list_id, item_type=item_type, q=q, page=page, page_size=page_size
    )
    return ok(items, page=page, page_size=page_size, total=total)


@router.put(
    "/price-lists/{price_list_id}/items",
    summary="Set a price",
    description="Closes the current price and opens a new one from `effective_from` (default "
    "now). A later scheduled change is replaced. History is kept.",
    responses=_ERR,
)
async def set_price(
    price_list_id: uuid.UUID, body: SetPriceIn, actor: PriceManager, db: Db
) -> Envelope[PriceItemOut]:
    return ok(await _svc(db, actor).set_price(price_list_id, body))


@router.delete(
    "/price-lists/{price_list_id}/items/{item_type}/{item_id}",
    status_code=NO_CONTENT,
    summary="Stop pricing an item in this list",
    description="A branch list then falls back to the default list; in the default list the "
    "item becomes unbookable.",
    responses=_ERR,
)
async def end_price(
    price_list_id: uuid.UUID,
    item_type: ItemType,
    item_id: uuid.UUID,
    actor: PriceManager,
    db: Db,
) -> Response:
    await _svc(db, actor).end_price(price_list_id, item_type, item_id)
    return Response(status_code=NO_CONTENT)


@router.get(
    "/price-lists/{price_list_id}/items/{item_type}/{item_id}/history",
    summary="Price history of an item",
    responses=_ERR,
)
async def price_history(
    price_list_id: uuid.UUID, item_type: ItemType, item_id: uuid.UUID, actor: PriceViewer, db: Db
) -> Envelope[list[PriceHistoryOut]]:
    return ok(await _svc(db, actor).price_history(price_list_id, item_type, item_id))
