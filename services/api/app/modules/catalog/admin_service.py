"""Catalog administration: master data, tests, parameters, reference ranges, packages,
health concerns, synonyms and price lists.

Every change is audited in the same transaction and invalidates the search cache after
commit. Guard rails enforced here (not in the UI):
- a test that belongs to an active package cannot be deleted or deactivated;
- reference ranges cannot overlap for identical criteria (also a DB exclusion constraint);
- prices are never rewritten: a change closes the current row and opens a new one;
- the default price list cannot be deactivated.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import Base, on_commit
from app.core.errors import (
    BusinessRuleViolation,
    Conflict,
    ErrorDetail,
    NotFound,
    ValidationFailed,
)
from app.core.sql import check_version, escape_like, integrity_to_app_error
from app.core.timeutil import utcnow
from app.modules.audit import service as audit
from app.modules.catalog.models import (
    Category,
    ConcernPackage,
    ConcernTest,
    Department,
    HealthConcern,
    Package,
    PackageTest,
    Preparation,
    PriceList,
    PriceListItem,
    ReferenceRange,
    SampleType,
    SearchSynonym,
    Test,
    TestParameter,
)
from app.modules.catalog.ranges import RangeRule, find_conflict
from app.modules.catalog.repository import CatalogReader, PriceScope
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
    ItemPrice,
    PackageIn,
    PackageUpdate,
    ParameterIn,
    ParameterOut,
    ParameterUpdate,
    PreparationIn,
    PreparationUpdate,
    Price,
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
    TestIn,
    TestUpdate,
)
from app.modules.catalog.service import invalidate_search_cache

M = TypeVar("M", bound=Base)
Out = TypeVar("Out", bound=BaseModel)


def _json(value: Any) -> Any:
    if isinstance(value, uuid.UUID | datetime | date | Decimal):
        return str(value)
    if isinstance(value, list):
        return [_json(v) for v in value]
    return value


def _snapshot(obj: object, fields: Iterable[str]) -> dict[str, Any]:
    return {f: _json(getattr(obj, f)) for f in fields}


def _dump(model: BaseModel, **kw: Any) -> dict[str, Any]:
    return {k: _json(v) for k, v in model.model_dump(**kw).items()}


def _rule(r: ReferenceRange | ReferenceRangeIn, rid: uuid.UUID) -> RangeRule:
    return RangeRule(
        id=rid,
        sex=r.sex,
        age_min_days=r.age_min_days,
        age_max_days=r.age_max_days,
        sample_type_id=r.sample_type_id,
        lab_id=r.lab_id,
        method=r.method,
        effective_from=r.effective_from or date.today(),
        effective_to=r.effective_to,
    )


class CatalogAdminService:
    def __init__(self, session: AsyncSession, actor_id: uuid.UUID, actor_roles: list[str]) -> None:
        self.s = session
        self.actor_id = actor_id
        self.actor_roles = actor_roles
        self._invalidation_queued = False

    # ---------------------------------------------------------------- plumbing
    def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: object,
        *,
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
    ) -> None:
        audit.record(
            self.s,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_user_id=self.actor_id,
            actor_roles=self.actor_roles,
            before=before,
            after=after,
        )
        if not self._invalidation_queued:
            on_commit(self.s, invalidate_search_cache)
            self._invalidation_queued = True

    async def _flush(self, **messages: str) -> None:
        try:
            await self.s.flush()
        except IntegrityError as exc:
            raise integrity_to_app_error(exc, **messages) from exc

    async def _get(self, model: type[M], obj_id: uuid.UUID, *, lock: bool = True) -> M:
        obj = await self.s.get(model, obj_id, with_for_update=lock)
        if obj is None or getattr(obj, "deleted_at", None) is not None:
            raise NotFound()
        return obj

    async def _require_refs(self, refs: Sequence[tuple[str, type[Base], uuid.UUID | None]]) -> None:
        details = []
        for field, model, ref_id in refs:
            if ref_id is not None and await self.s.get(model, ref_id) is None:
                details.append(ErrorDetail(field=field, issue="unknown reference"))
        if details:
            raise ValidationFailed(details=details)

    # ---------------------------------------------------------------- master data
    async def _list(self, model: type[M], out: type[Out], *order: Any) -> list[Out]:
        return [out.model_validate(r) for r in await self.s.scalars(select(model).order_by(*order))]

    async def _create(self, model: type[M], body: BaseModel, out: type[Out], entity: str) -> Out:
        obj = model(**body.model_dump())
        self.s.add(obj)
        await self._flush()
        self._audit(f"{entity}.created", entity, obj.id, after=_dump(body))  # type: ignore[attr-defined]
        return out.model_validate(obj)

    async def _update(
        self,
        model: type[M],
        obj_id: uuid.UUID,
        body: BaseModel,
        if_match: int | None,
        out: type[Out],
        entity: str,
    ) -> Out:
        obj: Any = await self._get(model, obj_id)
        check_version(obj.version, if_match)
        changes = body.model_dump(exclude_unset=True)
        before = _snapshot(obj, changes)
        for k, v in changes.items():
            setattr(obj, k, v)
        obj.version += 1
        await self._flush()
        self._audit(
            f"{entity}.updated",
            entity,
            obj.id,
            before=before,
            after=_dump(body, exclude_unset=True),
        )
        return out.model_validate(obj)

    async def list_departments(self) -> list[AdminDepartmentOut]:
        return await self._list(
            Department, AdminDepartmentOut, Department.sort_order, Department.name
        )

    async def create_department(self, body: DepartmentIn) -> AdminDepartmentOut:
        return await self._create(Department, body, AdminDepartmentOut, "department")

    async def update_department(
        self, obj_id: uuid.UUID, body: DepartmentUpdate, if_match: int | None
    ) -> AdminDepartmentOut:
        return await self._update(
            Department, obj_id, body, if_match, AdminDepartmentOut, "department"
        )

    async def list_categories(self) -> list[AdminCategoryOut]:
        return await self._list(Category, AdminCategoryOut, Category.sort_order, Category.name)

    async def create_category(self, body: CategoryIn) -> AdminCategoryOut:
        await self._require_refs([("parent_id", Category, body.parent_id)])
        return await self._create(Category, body, AdminCategoryOut, "category")

    async def update_category(
        self, obj_id: uuid.UUID, body: CategoryUpdate, if_match: int | None
    ) -> AdminCategoryOut:
        if body.parent_id is not None:
            if body.parent_id == obj_id:
                raise ValidationFailed(
                    details=[ErrorDetail(field="parent_id", issue="cannot be itself")]
                )
            await self._require_refs([("parent_id", Category, body.parent_id)])
            # Refuse cycles: walk up from the new parent.
            cursor: uuid.UUID | None = body.parent_id
            while cursor is not None:
                if cursor == obj_id:
                    raise ValidationFailed(
                        details=[ErrorDetail(field="parent_id", issue="creates a cycle")]
                    )
                cursor = await self.s.scalar(
                    select(Category.parent_id).where(Category.id == cursor)
                )
        return await self._update(Category, obj_id, body, if_match, AdminCategoryOut, "category")

    async def list_sample_types(self) -> list[AdminSampleTypeOut]:
        return await self._list(SampleType, AdminSampleTypeOut, SampleType.name)

    async def create_sample_type(self, body: SampleTypeIn) -> AdminSampleTypeOut:
        return await self._create(SampleType, body, AdminSampleTypeOut, "sample_type")

    async def update_sample_type(
        self, obj_id: uuid.UUID, body: SampleTypeUpdate, if_match: int | None
    ) -> AdminSampleTypeOut:
        return await self._update(
            SampleType, obj_id, body, if_match, AdminSampleTypeOut, "sample_type"
        )

    async def list_preparations(self) -> list[AdminPreparationOut]:
        return await self._list(Preparation, AdminPreparationOut, Preparation.title)

    async def create_preparation(self, body: PreparationIn) -> AdminPreparationOut:
        return await self._create(Preparation, body, AdminPreparationOut, "preparation")

    async def update_preparation(
        self, obj_id: uuid.UUID, body: PreparationUpdate, if_match: int | None
    ) -> AdminPreparationOut:
        return await self._update(
            Preparation, obj_id, body, if_match, AdminPreparationOut, "preparation"
        )

    # ---------------------------------------------------------------- pricing helpers
    async def _item_prices(self, item_type: str, item_id: uuid.UUID) -> list[ItemPrice]:
        ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
        now = utcnow()
        rows = await self.s.execute(
            select(PriceListItem, PriceList)
            .join(PriceList, PriceList.id == PriceListItem.price_list_id)
            .where(
                ref == item_id,
                PriceListItem.effective_from <= now,
                or_(PriceListItem.effective_to.is_(None), PriceListItem.effective_to > now),
            )
            .order_by(PriceList.branch_id.is_not(None), PriceList.name)
        )
        return [
            ItemPrice(
                price_list_id=pl.id,
                price_list_code=pl.code,
                price_list_name=pl.name,
                branch_id=pl.branch_id,
                price=Price(amount=item.price, mrp=item.mrp),
                effective_from=item.effective_from,
            )
            for item, pl in rows
        ]

    async def _default_reader(self) -> CatalogReader:
        return CatalogReader(self.s, await PriceScope.load(self.s))

    # ---------------------------------------------------------------- tests
    async def list_tests(
        self,
        *,
        q: str | None,
        department_id: uuid.UUID | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AdminTestListItem], int]:
        stmt = select(Test).where(Test.deleted_at.is_(None))
        if q:
            like = f"%{escape_like(q.strip().lower())}%"
            stmt = stmt.where(
                or_(
                    func.lower(Test.name).like(like, escape="\\"),
                    func.lower(Test.code).like(like, escape="\\"),
                    func.lower(func.coalesce(Test.aliases, "")).like(like, escape="\\"),
                )
            )
        if department_id:
            stmt = stmt.where(Test.department_id == department_id)
        if is_active is not None:
            stmt = stmt.where(Test.is_active.is_(is_active))
        total = await self.s.scalar(select(func.count()).select_from(stmt.subquery()))
        tests = list(
            await self.s.scalars(
                stmt.order_by(Test.name).offset((page - 1) * page_size).limit(page_size)
            )
        )
        summaries = await (await self._default_reader()).test_summaries(tests)
        items = [
            AdminTestListItem(
                id=t.id,
                code=t.code,
                slug=t.slug,
                name=t.name,
                name_bn=t.name_bn,
                department=s.department,
                sample_type=s.sample_type,
                tat_hours=t.tat_hours,
                parameter_count=s.parameter_count,
                is_active=t.is_active,
                is_featured=t.is_featured,
                price=s.price,
                version=t.version,
                updated_at=t.updated_at,
            )
            for t, s in zip(tests, summaries, strict=True)
        ]
        return items, int(total or 0)

    async def get_test(self, test_id: uuid.UUID) -> AdminTestOut:
        test = await self.s.scalar(
            select(Test)
            .where(Test.id == test_id, Test.deleted_at.is_(None))
            .options(selectinload(Test.parameters).selectinload(TestParameter.ranges))
            .execution_options(populate_existing=True)
        )
        if test is None:
            raise NotFound()
        concern_ids = await self.s.scalars(
            select(ConcernTest.concern_id).where(ConcernTest.test_id == test.id)
        )
        return AdminTestOut(
            **{
                f: getattr(test, f)
                for f in AdminTestOut.model_fields
                if hasattr(Test, f) and f != "parameters"
            },
            parameters=[ParameterOut.model_validate(p) for p in test.parameters],
            prices=await self._item_prices("TEST", test.id),
            concern_ids=list(concern_ids),
        )

    async def _test_refs(self, data: Mapping[str, Any]) -> None:
        await self._require_refs(
            [
                ("department_id", Department, data.get("department_id")),
                ("sample_type_id", SampleType, data.get("sample_type_id")),
                ("category_id", Category, data.get("category_id")),
                ("preparation_id", Preparation, data.get("preparation_id")),
            ]
        )

    async def create_test(self, body: TestIn) -> AdminTestOut:
        data = body.model_dump()
        await self._test_refs(data)
        test = Test(**data)
        self.s.add(test)
        await self._flush(duplicate="A test with this code or slug already exists.")
        self._audit("test.created", "test", test.id, after=_dump(body))
        return await self.get_test(test.id)

    async def _active_packages_with(self, test_id: uuid.UUID) -> list[str]:
        rows = await self.s.scalars(
            select(Package.name)
            .join(PackageTest, PackageTest.package_id == Package.id)
            .where(
                PackageTest.test_id == test_id,
                Package.deleted_at.is_(None),
                Package.is_active.is_(True),
            )
            .order_by(Package.name)
        )
        return list(rows)

    async def _guard_not_in_packages(self, test_id: uuid.UUID) -> None:
        packages = await self._active_packages_with(test_id)
        if packages:
            raise BusinessRuleViolation(
                f"This test is part of active packages: {', '.join(packages)}. "
                "Remove it from those packages first.",
                code="TEST_IN_ACTIVE_PACKAGES",
            )

    async def update_test(
        self, test_id: uuid.UUID, body: TestUpdate, if_match: int | None
    ) -> AdminTestOut:
        test = await self._get(Test, test_id)
        check_version(test.version, if_match)
        changes = body.model_dump(exclude_unset=True)
        for required in ("department_id", "sample_type_id", "tat_hours", "name", "slug"):
            if required in changes and changes[required] is None:
                raise ValidationFailed(
                    details=[ErrorDetail(field=required, issue="cannot be empty")]
                )
        await self._test_refs(changes)
        if changes.get("is_active") is False and test.is_active:
            await self._guard_not_in_packages(test.id)
        before = _snapshot(test, changes)
        for k, v in changes.items():
            setattr(test, k, v)
        if not (test.home_collection or test.centre_collection):
            raise ValidationFailed(
                details=[
                    ErrorDetail(field="home_collection", issue="a test needs a collection mode")
                ]
            )
        test.version += 1
        await self._flush(duplicate="A test with this slug already exists.")
        self._audit(
            "test.updated", "test", test.id, before=before, after=_dump(body, exclude_unset=True)
        )
        return await self.get_test(test.id)

    async def delete_test(self, test_id: uuid.UUID, if_match: int | None) -> None:
        test = await self._get(Test, test_id)
        check_version(test.version, if_match)
        await self._guard_not_in_packages(test.id)
        test.deleted_at = utcnow()
        test.is_active = False
        test.version += 1
        self._audit("test.deleted", "test", test.id, before={"code": test.code, "slug": test.slug})

    # ---------------------------------------------------------------- parameters
    async def add_parameter(self, test_id: uuid.UUID, body: ParameterIn) -> AdminTestOut:
        test = await self._get(Test, test_id)
        param = TestParameter(test_id=test.id, **body.model_dump())
        self.s.add(param)
        await self._flush(duplicate="This test already has a parameter with that code.")
        test.version += 1
        self._audit("test.parameter_added", "test", test.id, after={"parameter": _dump(body)})
        return await self.get_test(test.id)

    async def _parameter(self, parameter_id: uuid.UUID) -> TestParameter:
        param = await self.s.get(TestParameter, parameter_id, with_for_update=True)
        if param is None:
            raise NotFound()
        return param

    async def update_parameter(
        self, parameter_id: uuid.UUID, body: ParameterUpdate
    ) -> AdminTestOut:
        param = await self._parameter(parameter_id)
        changes = body.model_dump(exclude_unset=True)
        if "formula" in changes and (param.result_type == "CALCULATED") != bool(changes["formula"]):
            raise ValidationFailed(
                details=[
                    ErrorDetail(field="formula", issue="required for, and only for, CALCULATED")
                ]
            )
        if "options" in changes and param.result_type == "OPTION" and not changes["options"]:
            raise ValidationFailed(
                details=[ErrorDetail(field="options", issue="at least one option")]
            )
        before = _snapshot(param, changes)
        for k, v in changes.items():
            setattr(param, k, v)
        await self._flush()
        self._audit(
            "test.parameter_updated",
            "test",
            param.test_id,
            before={"parameter": param.code, **before},
            after={"parameter": param.code, **_dump(body, exclude_unset=True)},
        )
        return await self.get_test(param.test_id)

    async def delete_parameter(self, parameter_id: uuid.UUID) -> AdminTestOut:
        param = await self._parameter(parameter_id)
        test_id = param.test_id
        self._audit("test.parameter_deleted", "test", test_id, before={"parameter": param.code})
        await self.s.delete(param)
        await self._flush()
        return await self.get_test(test_id)

    # ---------------------------------------------------------------- reference ranges
    async def _check_range(
        self, parameter_id: uuid.UUID, body: ReferenceRangeIn, range_id: uuid.UUID
    ) -> None:
        await self._require_refs([("sample_type_id", SampleType, body.sample_type_id)])
        existing = await self.s.scalars(
            select(ReferenceRange).where(ReferenceRange.parameter_id == parameter_id)
        )
        conflict = find_conflict(_rule(body, range_id), [_rule(r, r.id) for r in existing])
        if conflict is not None:
            raise Conflict(
                "Another range with the same criteria already covers part of this age band "
                "and period. Narrow the age band or end the other range first.",
                code="REFERENCE_RANGE_OVERLAP",
                details=[ErrorDetail(field="age_min_days", issue=f"overlaps range {conflict.id}")],
            )

    async def add_range(self, parameter_id: uuid.UUID, body: ReferenceRangeIn) -> AdminTestOut:
        param = await self._parameter(parameter_id)
        if param.result_type not in ("NUMERIC", "CALCULATED") and (body.low or body.high):
            raise ValidationFailed(
                details=[ErrorDetail(field="low", issue="numeric limits need a numeric parameter")]
            )
        new_id = uuid.uuid4()
        await self._check_range(param.id, body, new_id)
        data = body.model_dump(exclude_none=True)
        rng = ReferenceRange(parameter_id=param.id, **data)
        self.s.add(rng)
        await self._flush(
            overlap_code="REFERENCE_RANGE_OVERLAP", overlap="Overlapping reference range."
        )
        self._audit(
            "reference_range.created",
            "reference_range",
            rng.id,
            after={"parameter_id": str(param.id), **_dump(body)},
        )
        return await self.get_test(param.test_id)

    async def update_range(
        self, range_id: uuid.UUID, body: ReferenceRangeIn, if_match: int | None
    ) -> AdminTestOut:
        rng = await self.s.get(ReferenceRange, range_id, with_for_update=True)
        if rng is None:
            raise NotFound()
        check_version(rng.version, if_match)
        await self._check_range(rng.parameter_id, body, rng.id)
        fields = ReferenceRangeIn.model_fields.keys()
        before = _snapshot(rng, fields)
        data = body.model_dump()
        if data["effective_from"] is None:
            data["effective_from"] = rng.effective_from
        for k, v in data.items():
            setattr(rng, k, v)
        rng.version += 1
        await self._flush(
            overlap_code="REFERENCE_RANGE_OVERLAP", overlap="Overlapping reference range."
        )
        self._audit(
            "reference_range.updated", "reference_range", rng.id, before=before, after=_dump(body)
        )
        param = await self.s.get(TestParameter, rng.parameter_id)
        assert param is not None
        return await self.get_test(param.test_id)

    async def delete_range(self, range_id: uuid.UUID) -> AdminTestOut:
        rng = await self.s.get(ReferenceRange, range_id, with_for_update=True)
        if rng is None:
            raise NotFound()
        param = await self.s.get(TestParameter, rng.parameter_id)
        assert param is not None
        self._audit(
            "reference_range.deleted",
            "reference_range",
            rng.id,
            before=_snapshot(rng, ReferenceRangeIn.model_fields.keys()),
        )
        await self.s.delete(rng)
        await self._flush()
        return await self.get_test(param.test_id)

    # ---------------------------------------------------------------- packages
    async def _validate_tests(self, test_ids: Sequence[uuid.UUID], field: str = "test_ids") -> None:
        if not test_ids:
            return
        found = set(
            await self.s.scalars(
                select(Test.id).where(Test.id.in_(set(test_ids)), Test.deleted_at.is_(None))
            )
        )
        missing = [str(t) for t in test_ids if t not in found]
        if missing:
            raise ValidationFailed(
                details=[ErrorDetail(field=field, issue=f"unknown test(s): {', '.join(missing)}")]
            )

    async def _set_package_tests(
        self, package_id: uuid.UUID, test_ids: Sequence[uuid.UUID]
    ) -> None:
        await self.s.execute(delete(PackageTest).where(PackageTest.package_id == package_id))
        self.s.add_all(
            PackageTest(package_id=package_id, test_id=t, sort_order=i)
            for i, t in enumerate(test_ids)
        )

    async def list_packages(
        self, *, q: str | None, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[AdminPackageListItem], int]:
        stmt = select(Package).where(Package.deleted_at.is_(None))
        if q:
            like = f"%{escape_like(q.strip().lower())}%"
            stmt = stmt.where(
                or_(
                    func.lower(Package.name).like(like, escape="\\"),
                    func.lower(Package.code).like(like, escape="\\"),
                )
            )
        if is_active is not None:
            stmt = stmt.where(Package.is_active.is_(is_active))
        total = await self.s.scalar(select(func.count()).select_from(stmt.subquery()))
        packages = list(
            await self.s.scalars(
                stmt.order_by(Package.name).offset((page - 1) * page_size).limit(page_size)
            )
        )
        summaries = await (await self._default_reader()).package_summaries(packages)
        return [
            AdminPackageListItem(
                id=p.id,
                code=p.code,
                slug=p.slug,
                name=p.name,
                name_bn=p.name_bn,
                test_count=s.test_count,
                is_active=p.is_active,
                is_featured=p.is_featured,
                price=s.price,
                tests_total=s.tests_total,
                version=p.version,
                updated_at=p.updated_at,
            )
            for p, s in zip(packages, summaries, strict=True)
        ], int(total or 0)

    async def get_package(self, package_id: uuid.UUID) -> AdminPackageOut:
        package = await self.s.scalar(
            select(Package)
            .where(Package.id == package_id, Package.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        if package is None:
            raise NotFound()
        test_ids = await self.s.scalars(
            select(PackageTest.test_id)
            .where(PackageTest.package_id == package.id)
            .order_by(PackageTest.sort_order)
        )
        summary = (await (await self._default_reader()).package_summaries([package]))[0]
        return AdminPackageOut(
            **{f: getattr(package, f) for f in AdminPackageOut.model_fields if hasattr(Package, f)},
            test_ids=list(test_ids),
            prices=await self._item_prices("PACKAGE", package.id),
            tests_total=summary.tests_total,
        )

    async def create_package(self, body: PackageIn) -> AdminPackageOut:
        await self._validate_tests(body.test_ids)
        package = Package(**body.model_dump(exclude={"test_ids"}))
        self.s.add(package)
        await self._flush(duplicate="A package with this code or slug already exists.")
        await self._set_package_tests(package.id, body.test_ids)
        await self._flush()
        self._audit("package.created", "package", package.id, after=_dump(body))
        return await self.get_package(package.id)

    async def update_package(
        self, package_id: uuid.UUID, body: PackageUpdate, if_match: int | None
    ) -> AdminPackageOut:
        package = await self._get(Package, package_id)
        check_version(package.version, if_match)
        changes = body.model_dump(exclude_unset=True, exclude={"test_ids"})
        for required in ("name", "slug"):
            if required in changes and changes[required] is None:
                raise ValidationFailed(
                    details=[ErrorDetail(field=required, issue="cannot be empty")]
                )
        before = _snapshot(package, changes)
        for k, v in changes.items():
            setattr(package, k, v)
        if (
            package.age_min_years is not None
            and package.age_max_years is not None
            and package.age_min_years > package.age_max_years
        ):
            raise ValidationFailed(
                details=[ErrorDetail(field="age_min_years", issue="exceeds max")]
            )
        if body.test_ids is not None:
            if len(set(body.test_ids)) != len(body.test_ids):
                raise ValidationFailed(details=[ErrorDetail(field="test_ids", issue="duplicates")])
            await self._validate_tests(body.test_ids)
            before["test_ids"] = [
                str(t)
                for t in await self.s.scalars(
                    select(PackageTest.test_id).where(PackageTest.package_id == package.id)
                )
            ]
            await self._set_package_tests(package.id, body.test_ids)
        package.version += 1
        await self._flush(duplicate="A package with this slug already exists.")
        self._audit(
            "package.updated",
            "package",
            package.id,
            before=before,
            after=_dump(body, exclude_unset=True),
        )
        return await self.get_package(package.id)

    async def delete_package(self, package_id: uuid.UUID, if_match: int | None) -> None:
        package = await self._get(Package, package_id)
        check_version(package.version, if_match)
        package.deleted_at = utcnow()
        package.is_active = False
        package.version += 1
        self._audit("package.deleted", "package", package.id, before={"code": package.code})

    # ---------------------------------------------------------------- concerns
    async def _concern_out(self, concern: HealthConcern) -> AdminConcernOut:
        test_ids = await self.s.scalars(
            select(ConcernTest.test_id).where(ConcernTest.concern_id == concern.id)
        )
        package_ids = await self.s.scalars(
            select(ConcernPackage.package_id).where(ConcernPackage.concern_id == concern.id)
        )
        return AdminConcernOut(
            **{
                f: getattr(concern, f)
                for f in AdminConcernOut.model_fields
                if hasattr(HealthConcern, f)
            },
            test_ids=list(test_ids),
            package_ids=list(package_ids),
        )

    async def _set_concern_links(
        self,
        concern_id: uuid.UUID,
        test_ids: Sequence[uuid.UUID] | None,
        package_ids: Sequence[uuid.UUID] | None,
    ) -> None:
        if test_ids is not None:
            await self._validate_tests(test_ids)
            await self.s.execute(delete(ConcernTest).where(ConcernTest.concern_id == concern_id))
            self.s.add_all(ConcernTest(concern_id=concern_id, test_id=t) for t in set(test_ids))
        if package_ids is not None:
            found = set(
                await self.s.scalars(
                    select(Package.id).where(
                        Package.id.in_(set(package_ids)), Package.deleted_at.is_(None)
                    )
                )
            )
            if found != set(package_ids):
                raise ValidationFailed(
                    details=[ErrorDetail(field="package_ids", issue="unknown package")]
                )
            await self.s.execute(
                delete(ConcernPackage).where(ConcernPackage.concern_id == concern_id)
            )
            self.s.add_all(ConcernPackage(concern_id=concern_id, package_id=p) for p in found)

    async def list_concerns(self) -> list[AdminConcernOut]:
        rows = await self.s.scalars(
            select(HealthConcern)
            .where(HealthConcern.deleted_at.is_(None))
            .order_by(HealthConcern.sort_order, HealthConcern.name)
        )
        return [await self._concern_out(c) for c in rows]

    async def create_concern(self, body: ConcernIn) -> AdminConcernOut:
        concern = HealthConcern(**body.model_dump(exclude={"test_ids", "package_ids"}))
        self.s.add(concern)
        await self._flush(duplicate="A health concern with this slug already exists.")
        await self._set_concern_links(concern.id, body.test_ids, body.package_ids)
        await self._flush()
        self._audit("concern.created", "health_concern", concern.id, after=_dump(body))
        return await self._concern_out(concern)

    async def update_concern(
        self, concern_id: uuid.UUID, body: ConcernUpdate, if_match: int | None
    ) -> AdminConcernOut:
        concern = await self._get(HealthConcern, concern_id)
        check_version(concern.version, if_match)
        changes = body.model_dump(exclude_unset=True, exclude={"test_ids", "package_ids"})
        before = _snapshot(concern, changes)
        for k, v in changes.items():
            setattr(concern, k, v)
        await self._set_concern_links(concern.id, body.test_ids, body.package_ids)
        concern.version += 1
        await self._flush(duplicate="A health concern with this slug already exists.")
        self._audit(
            "concern.updated",
            "health_concern",
            concern.id,
            before=before,
            after=_dump(body, exclude_unset=True),
        )
        return await self._concern_out(concern)

    async def delete_concern(self, concern_id: uuid.UUID, if_match: int | None) -> None:
        concern = await self._get(HealthConcern, concern_id)
        check_version(concern.version, if_match)
        concern.deleted_at = utcnow()
        concern.is_active = False
        concern.version += 1
        await self.s.execute(
            delete(SearchSynonym).where(
                SearchSynonym.target_type == "CONCERN", SearchSynonym.target_id == concern.id
            )
        )
        self._audit("concern.deleted", "health_concern", concern.id, before={"slug": concern.slug})

    # ---------------------------------------------------------------- synonyms
    _TARGETS: Mapping[str, Any] = {"TEST": Test, "PACKAGE": Package, "CONCERN": HealthConcern}

    async def list_synonyms(
        self, *, q: str | None, target_type: str | None, target_id: uuid.UUID | None
    ) -> list[SynonymOut]:
        stmt = select(SearchSynonym).order_by(SearchSynonym.term)
        if q:
            stmt = stmt.where(SearchSynonym.term.like(f"%{escape_like(q.lower())}%", escape="\\"))
        if target_type:
            stmt = stmt.where(SearchSynonym.target_type == target_type)
        if target_id:
            stmt = stmt.where(SearchSynonym.target_id == target_id)
        rows = list(await self.s.scalars(stmt.limit(500)))
        names: dict[uuid.UUID, str] = {}
        for kind, model in self._TARGETS.items():
            ids = {r.target_id for r in rows if r.target_type == kind}
            if ids:
                names.update(
                    dict(
                        (
                            await self.s.execute(
                                select(model.id, model.name).where(model.id.in_(ids))
                            )
                        ).all()
                    )
                )
        return [
            SynonymOut(
                id=r.id,
                term=r.term,
                target_type=r.target_type,
                target_id=r.target_id,
                target_name=names.get(r.target_id, "?"),
            )
            for r in rows
        ]

    async def create_synonym(self, body: SynonymIn) -> SynonymOut:
        model = self._TARGETS[body.target_type]
        target = await self.s.get(model, body.target_id)
        if target is None or target.deleted_at is not None:
            raise ValidationFailed(details=[ErrorDetail(field="target_id", issue="unknown target")])
        synonym = SearchSynonym(**body.model_dump())
        self.s.add(synonym)
        await self._flush(duplicate="This synonym already exists for that target.")
        self._audit("synonym.created", "search_synonym", synonym.id, after=_dump(body))
        return SynonymOut(
            id=synonym.id,
            term=synonym.term,
            target_type=body.target_type,
            target_id=synonym.target_id,
            target_name=target.name,
        )

    async def delete_synonym(self, synonym_id: uuid.UUID) -> None:
        synonym = await self.s.get(SearchSynonym, synonym_id)
        if synonym is None:
            raise NotFound()
        self._audit(
            "synonym.deleted",
            "search_synonym",
            synonym.id,
            before={
                "term": synonym.term,
                "target_type": synonym.target_type,
                "target_id": str(synonym.target_id),
            },
        )
        await self.s.delete(synonym)

    # ---------------------------------------------------------------- price lists
    async def _price_list_out(self, pl: PriceList) -> PriceListOut:
        now = utcnow()
        count = await self.s.scalar(
            select(func.count())
            .select_from(PriceListItem)
            .where(
                PriceListItem.price_list_id == pl.id,
                PriceListItem.effective_from <= now,
                or_(PriceListItem.effective_to.is_(None), PriceListItem.effective_to > now),
            )
        )
        return PriceListOut(
            id=pl.id,
            code=pl.code,
            name=pl.name,
            branch_id=pl.branch_id,
            is_active=pl.is_active,
            version=pl.version,
            item_count=int(count or 0),
        )

    async def list_price_lists(self) -> list[PriceListOut]:
        rows = await self.s.scalars(
            select(PriceList).order_by(PriceList.branch_id.is_not(None), PriceList.name)
        )
        return [await self._price_list_out(pl) for pl in rows]

    async def create_price_list(self, body: PriceListIn) -> PriceListOut:
        pl = PriceList(**body.model_dump())
        self.s.add(pl)
        await self._flush(duplicate="That code is taken, or this branch already has a price list.")
        self._audit("price_list.created", "price_list", pl.id, after=_dump(body))
        return await self._price_list_out(pl)

    async def update_price_list(
        self, price_list_id: uuid.UUID, body: PriceListUpdate, if_match: int | None
    ) -> PriceListOut:
        pl = await self._get(PriceList, price_list_id)
        check_version(pl.version, if_match)
        if body.is_active is False and pl.branch_id is None:
            raise BusinessRuleViolation(
                "The default price list must stay active.", code="DEFAULT_PRICE_LIST_REQUIRED"
            )
        changes = body.model_dump(exclude_unset=True)
        before = _snapshot(pl, changes)
        for k, v in changes.items():
            setattr(pl, k, v)
        pl.version += 1
        self._audit("price_list.updated", "price_list", pl.id, before=before, after=changes)
        return await self._price_list_out(pl)

    async def list_price_items(
        self,
        price_list_id: uuid.UUID,
        *,
        item_type: str,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PriceItemOut], int]:
        await self._get(PriceList, price_list_id, lock=False)
        model: Any = Test if item_type == "TEST" else Package
        ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
        stmt = select(model).where(model.deleted_at.is_(None))
        if q:
            like = f"%{escape_like(q.strip().lower())}%"
            stmt = stmt.where(
                or_(
                    func.lower(model.name).like(like, escape="\\"),
                    func.lower(model.code).like(like, escape="\\"),
                )
            )
        total = await self.s.scalar(select(func.count()).select_from(stmt.subquery()))
        items: list[Any] = list(
            await self.s.scalars(
                stmt.order_by(model.name).offset((page - 1) * page_size).limit(page_size)
            )
        )
        now = utcnow()
        rows = await self.s.scalars(
            select(PriceListItem)
            .where(
                PriceListItem.price_list_id == price_list_id,
                ref.in_([i.id for i in items]),
                or_(PriceListItem.effective_to.is_(None), PriceListItem.effective_to > now),
            )
            .order_by(PriceListItem.effective_from)
        )
        current: dict[uuid.UUID, PriceListItem] = {}
        scheduled: dict[uuid.UUID, PriceListItem] = {}
        for row in rows:
            item_id = row.test_id or row.package_id
            assert item_id is not None
            if row.effective_from <= now:
                current[item_id] = row
            else:
                scheduled.setdefault(item_id, row)
        out = []
        for i in items:
            c, s = current.get(i.id), scheduled.get(i.id)
            out.append(
                PriceItemOut(
                    item_type=item_type,
                    item_id=i.id,
                    code=i.code,
                    name=i.name,
                    is_active=i.is_active,
                    current=Price(amount=c.price, mrp=c.mrp) if c else None,
                    current_since=c.effective_from if c else None,
                    scheduled=Price(amount=s.price, mrp=s.mrp) if s else None,
                    scheduled_from=s.effective_from if s else None,
                )
            )
        return out, int(total or 0)

    async def _lock_item_rows(
        self, price_list_id: uuid.UUID, item_type: str, item_id: uuid.UUID
    ) -> list[PriceListItem]:
        ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
        rows = await self.s.scalars(
            select(PriceListItem)
            .where(
                PriceListItem.price_list_id == price_list_id,
                ref == item_id,
                or_(PriceListItem.effective_to.is_(None), PriceListItem.effective_to > utcnow()),
            )
            .with_for_update()
        )
        return list(rows)

    async def set_price(self, price_list_id: uuid.UUID, body: SetPriceIn) -> PriceItemOut:
        pl = await self._get(PriceList, price_list_id)
        model: Any = Test if body.item_type == "TEST" else Package
        item = await self.s.get(model, body.item_id)
        if item is None or item.deleted_at is not None:
            raise ValidationFailed(details=[ErrorDetail(field="item_id", issue="unknown item")])
        now = utcnow()
        start = body.effective_from.astimezone(UTC) if body.effective_from else now
        if start < now.replace(microsecond=0):
            raise ValidationFailed(
                details=[ErrorDetail(field="effective_from", issue="cannot be in the past")]
            )
        before = []
        for row in await self._lock_item_rows(pl.id, body.item_type, body.item_id):
            before.append({"price": row.price, "mrp": row.mrp, "from": str(row.effective_from)})
            if row.effective_from >= start:
                await self.s.delete(row)  # a not-yet-effective row replaced by this change
            else:
                row.effective_to = start
        await self._flush()
        self.s.add(
            PriceListItem(
                price_list_id=pl.id,
                item_type=body.item_type,
                test_id=item.id if body.item_type == "TEST" else None,
                package_id=item.id if body.item_type == "PACKAGE" else None,
                mrp=body.mrp,
                price=body.price,
                effective_from=start,
                created_by=self.actor_id,
            )
        )
        await self._flush(
            overlap_code="PRICE_OVERLAP", overlap="Another price change is in progress."
        )
        self._audit(
            "price.set",
            "price_list",
            pl.id,
            before={"item": f"{body.item_type}:{item.code}", "open_rows": before},
            after={"item": f"{body.item_type}:{item.code}", **_dump(body)},
        )
        items, _ = await self.list_price_items(
            pl.id, item_type=body.item_type, q=item.code, page=1, page_size=50
        )
        return next(i for i in items if i.item_id == item.id)

    async def end_price(self, price_list_id: uuid.UUID, item_type: str, item_id: uuid.UUID) -> None:
        pl = await self._get(PriceList, price_list_id)
        now = utcnow()
        rows = await self._lock_item_rows(pl.id, item_type, item_id)
        if not rows:
            raise NotFound()
        for row in rows:
            if row.effective_from >= now:
                await self.s.delete(row)
            else:
                row.effective_to = now
        self._audit("price.ended", "price_list", pl.id, before={"item": f"{item_type}:{item_id}"})

    async def price_history(
        self, price_list_id: uuid.UUID, item_type: str, item_id: uuid.UUID
    ) -> list[PriceHistoryOut]:
        ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
        rows = await self.s.scalars(
            select(PriceListItem)
            .where(PriceListItem.price_list_id == price_list_id, ref == item_id)
            .order_by(PriceListItem.effective_from.desc())
            .limit(100)
        )
        return [
            PriceHistoryOut(
                price=Price(amount=r.price, mrp=r.mrp),
                effective_from=r.effective_from,
                effective_to=r.effective_to,
                created_at=r.created_at,
            )
            for r in rows
        ]
