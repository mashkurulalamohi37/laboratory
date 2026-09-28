"""Catalog read queries: pricing resolution and bulk summary builders (no N+1 queries)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import BigInteger, ColumnElement, and_, cast, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import (
    ConcernPackage,
    ConcernTest,
    Department,
    HealthConcern,
    Package,
    PackageTest,
    Preparation,
    PriceList,
    PriceListItem,
    SampleType,
    Test,
    TestParameter,
)
from app.modules.catalog.schemas import (
    ConcernRef,
    ConcernSummary,
    DepartmentOut,
    PackageSummary,
    Price,
    SampleTypeOut,
    TestSummary,
)


def visible_tests() -> list[ColumnElement[bool]]:
    return [Test.is_active.is_(True), Test.deleted_at.is_(None)]


def visible_packages() -> list[ColumnElement[bool]]:
    return [Package.is_active.is_(True), Package.deleted_at.is_(None)]


def visible_concerns() -> list[ColumnElement[bool]]:
    return [HealthConcern.is_active.is_(True), HealthConcern.deleted_at.is_(None)]


def _current() -> ColumnElement[bool]:
    now = func.now()
    return and_(
        PriceListItem.effective_from <= now,
        or_(PriceListItem.effective_to.is_(None), PriceListItem.effective_to > now),
    )


@dataclass(frozen=True, slots=True)
class PriceScope:
    """Price lists consulted in order: the branch list (if any) then the default list."""

    list_ids: tuple[uuid.UUID, ...]

    @classmethod
    async def load(cls, session: AsyncSession, branch_id: uuid.UUID | None = None) -> PriceScope:
        rows = (
            await session.execute(
                select(PriceList.id, PriceList.branch_id).where(
                    PriceList.is_active.is_(True),
                    or_(PriceList.branch_id.is_(None), PriceList.branch_id == branch_id)
                    if branch_id
                    else PriceList.branch_id.is_(None),
                )
            )
        ).all()
        ordered = sorted(rows, key=lambda r: r.branch_id is None)  # branch list first
        return cls(tuple(r.id for r in ordered))

    def amount_expr(self, item_type: str, item_id: Any) -> ColumnElement[Any]:
        """SQL expression for the effective price of each row (for filtering/sorting)."""
        ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
        subqueries = [
            select(PriceListItem.price)
            .where(PriceListItem.price_list_id == list_id, ref == item_id, _current())
            .limit(1)
            .scalar_subquery()
            for list_id in self.list_ids
        ]
        if not subqueries:
            return cast(null(), BigInteger)
        return func.coalesce(*subqueries) if len(subqueries) > 1 else subqueries[0]

    async def prices(
        self, session: AsyncSession, item_type: str, ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, Price]:
        wanted = set(ids)
        if not wanted or not self.list_ids:
            return {}
        ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
        rows = (
            await session.execute(
                select(
                    ref, PriceListItem.price_list_id, PriceListItem.price, PriceListItem.mrp
                ).where(
                    PriceListItem.price_list_id.in_(self.list_ids),
                    PriceListItem.item_type == item_type,
                    ref.in_(wanted),
                    _current(),
                )
            )
        ).all()
        rank = {list_id: i for i, list_id in enumerate(self.list_ids)}
        best: dict[uuid.UUID, tuple[int, Price]] = {}
        for item_id, list_id, price, mrp in rows:
            if item_id is None:
                continue
            r = rank[list_id]
            if item_id not in best or r < best[item_id][0]:
                best[item_id] = (r, Price(amount=price, mrp=mrp))
        return {k: v[1] for k, v in best.items()}


class CatalogReader:
    def __init__(self, session: AsyncSession, prices: PriceScope) -> None:
        self.s = session
        self.price_scope = prices

    # ---------------------------------------------------------------- tests
    async def test_summaries(self, tests: Sequence[Test]) -> list[TestSummary]:
        if not tests:
            return []
        ids = [t.id for t in tests]
        departments = {
            d.id: d
            for d in await self.s.scalars(
                select(Department).where(Department.id.in_({t.department_id for t in tests}))
            )
        }
        samples = {
            s.id: s
            for s in await self.s.scalars(
                select(SampleType).where(SampleType.id.in_({t.sample_type_id for t in tests}))
            )
        }
        prep_ids = {t.preparation_id for t in tests if t.preparation_id}
        fasting = (
            {
                p.id: p.fasting_hours
                for p in await self.s.scalars(
                    select(Preparation).where(Preparation.id.in_(prep_ids))
                )
            }
            if prep_ids
            else {}
        )
        counts = dict(
            (
                await self.s.execute(
                    select(TestParameter.test_id, func.count())
                    .where(TestParameter.test_id.in_(ids), TestParameter.is_active.is_(True))
                    .group_by(TestParameter.test_id)
                )
            ).all()
        )
        prices = await self.price_scope.prices(self.s, "TEST", ids)
        return [
            TestSummary(
                id=t.id,
                code=t.code,
                slug=t.slug,
                name=t.name,
                name_bn=t.name_bn,
                short_description=t.short_description,
                short_description_bn=t.short_description_bn,
                department=DepartmentOut.model_validate(departments[t.department_id]),
                sample_type=SampleTypeOut.model_validate(samples[t.sample_type_id]),
                tat_hours=t.tat_hours,
                home_collection=t.home_collection,
                centre_collection=t.centre_collection,
                fasting_hours=fasting.get(t.preparation_id) if t.preparation_id else None,
                parameter_count=counts.get(t.id, 0),
                is_featured=t.is_featured,
                price=prices.get(t.id),
            )
            for t in tests
        ]

    # ---------------------------------------------------------------- packages
    async def package_tests(self, package_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[Test]]:
        """Visible tests of each package, in package order."""
        rows = await self.s.execute(
            select(PackageTest.package_id, Test)
            .join(Test, Test.id == PackageTest.test_id)
            .where(PackageTest.package_id.in_(set(package_ids)), *visible_tests())
            .order_by(PackageTest.sort_order, Test.name)
        )
        out: dict[uuid.UUID, list[Test]] = defaultdict(list)
        for package_id, test in rows:
            out[package_id].append(test)
        return out

    async def package_summaries(self, packages: Sequence[Package]) -> list[PackageSummary]:
        if not packages:
            return []
        members = await self.package_tests(p.id for p in packages)
        all_tests = {t.id: t for tests in members.values() for t in tests}
        counts = (
            dict(
                (
                    await self.s.execute(
                        select(TestParameter.test_id, func.count())
                        .where(
                            TestParameter.test_id.in_(all_tests.keys()),
                            TestParameter.is_active.is_(True),
                        )
                        .group_by(TestParameter.test_id)
                    )
                ).all()
            )
            if all_tests
            else {}
        )
        prep_ids = {t.preparation_id for t in all_tests.values() if t.preparation_id}
        fasting = (
            {
                p.id: p.fasting_hours
                for p in await self.s.scalars(
                    select(Preparation).where(Preparation.id.in_(prep_ids))
                )
            }
            if prep_ids
            else {}
        )
        test_prices = await self.price_scope.prices(self.s, "TEST", all_tests.keys())
        package_prices = await self.price_scope.prices(self.s, "PACKAGE", [p.id for p in packages])

        out = []
        for p in packages:
            tests = members.get(p.id, [])
            hours = [fasting.get(t.preparation_id) for t in tests if t.preparation_id]
            known = [h for h in hours if h]
            priced = [test_prices[t.id].amount for t in tests if t.id in test_prices]
            out.append(
                PackageSummary(
                    id=p.id,
                    code=p.code,
                    slug=p.slug,
                    name=p.name,
                    name_bn=p.name_bn,
                    short_description=p.short_description,
                    short_description_bn=p.short_description_bn,
                    test_count=len(tests),
                    parameter_count=sum(counts.get(t.id, 0) for t in tests),
                    sex=p.sex,
                    age_min_years=p.age_min_years,
                    age_max_years=p.age_max_years,
                    fasting_hours=max(known) if known else None,
                    home_collection=bool(tests) and all(t.home_collection for t in tests),
                    is_featured=p.is_featured,
                    price=package_prices.get(p.id),
                    tests_total=sum(priced) if tests and len(priced) == len(tests) else None,
                )
            )
        return out

    # ---------------------------------------------------------------- concerns
    async def concern_summaries(self, concerns: Sequence[HealthConcern]) -> list[ConcernSummary]:
        if not concerns:
            return []
        ids = [c.id for c in concerns]
        test_counts = dict(
            (
                await self.s.execute(
                    select(ConcernTest.concern_id, func.count())
                    .join(Test, Test.id == ConcernTest.test_id)
                    .where(ConcernTest.concern_id.in_(ids), *visible_tests())
                    .group_by(ConcernTest.concern_id)
                )
            ).all()
        )
        package_counts = dict(
            (
                await self.s.execute(
                    select(ConcernPackage.concern_id, func.count())
                    .join(Package, Package.id == ConcernPackage.package_id)
                    .where(ConcernPackage.concern_id.in_(ids), *visible_packages())
                    .group_by(ConcernPackage.concern_id)
                )
            ).all()
        )
        return [
            ConcernSummary(
                id=c.id,
                slug=c.slug,
                name=c.name,
                name_bn=c.name_bn,
                icon=c.icon,
                description=c.description,
                description_bn=c.description_bn,
                is_featured=c.is_featured,
                test_count=test_counts.get(c.id, 0),
                package_count=package_counts.get(c.id, 0),
            )
            for c in concerns
        ]

    async def concern_refs_for(
        self, *, test_id: uuid.UUID | None = None, package_id: uuid.UUID | None = None
    ) -> list[ConcernRef]:
        stmt = select(HealthConcern).where(*visible_concerns()).order_by(HealthConcern.sort_order)
        if test_id:
            stmt = stmt.join(ConcernTest, ConcernTest.concern_id == HealthConcern.id).where(
                ConcernTest.test_id == test_id
            )
        if package_id:
            stmt = stmt.join(ConcernPackage, ConcernPackage.concern_id == HealthConcern.id).where(
                ConcernPackage.package_id == package_id
            )
        return [ConcernRef.model_validate(c) for c in await self.s.scalars(stmt)]
