"""Public API of the catalog module: patient-facing reads, search, and lookups other
modules use (pricing, sitemap). Admin writes live in `admin_service`."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import ColumnElement, Float, String, and_, case, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import SEARCH_NAMESPACE, bump_namespace
from app.core.errors import NotFound
from app.core.sql import escape_like, nfc
from app.core.text import normalize_query, prefix_tsquery
from app.modules.catalog.models import (
    Category,
    ConcernPackage,
    ConcernTest,
    Department,
    HealthConcern,
    Package,
    PackageTest,
    Preparation,
    SampleType,
    SearchSynonym,
    Test,
    TestParameter,
)
from app.modules.catalog.repository import (
    CatalogReader,
    PriceScope,
    visible_concerns,
    visible_packages,
    visible_tests,
)
from app.modules.catalog.schemas import (
    CatalogFilters,
    CategoryOut,
    ConcernDetail,
    ConcernRef,
    ConcernSummary,
    DepartmentOut,
    PackageDetail,
    PackageSummary,
    ParameterPublic,
    PreparationOut,
    SampleTypeOut,
    TestDetail,
    TestSummary,
)

TestSort = Literal["popular", "name", "price_asc", "price_desc", "tat", "relevance"]
PackageSort = Literal["popular", "name", "price_asc", "price_desc"]


async def invalidate_search_cache() -> None:
    await bump_namespace(SEARCH_NAMESPACE)


@dataclass(frozen=True, slots=True)
class TestFilters:
    __test__ = False

    q: str | None = None
    department: str | None = None
    category: str | None = None
    sample_type: str | None = None
    concern: str | None = None
    home_collection: bool | None = None
    tat_max: int | None = None
    price_min: int | None = None
    price_max: int | None = None
    featured: bool | None = None


@dataclass(frozen=True, slots=True)
class PackageFilters:
    q: str | None = None
    sex: str | None = None
    age: int | None = None
    concern: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    featured: bool | None = None


@dataclass(frozen=True, slots=True)
class SearchHits:
    tests: list[TestSummary]
    packages: list[PackageSummary]
    concerns: list[ConcernSummary]


def _like(q: str) -> str:
    return f"%{escape_like(q)}%"


class CatalogService:
    def __init__(self, session: AsyncSession, prices: PriceScope) -> None:
        self.s = session
        self.prices = prices
        self.reader = CatalogReader(session, prices)

    @classmethod
    async def create(
        cls, session: AsyncSession, branch_id: uuid.UUID | None = None
    ) -> CatalogService:
        return cls(session, await PriceScope.load(session, branch_id))

    # ---------------------------------------------------------------- facets
    async def filters(self) -> CatalogFilters:
        departments = await self.s.scalars(
            select(Department)
            .where(Department.is_active.is_(True))
            .order_by(Department.sort_order, Department.name)
        )
        categories = await self.s.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order, Category.name)
        )
        samples = await self.s.scalars(
            select(SampleType).where(SampleType.is_active.is_(True)).order_by(SampleType.name)
        )
        concerns = await self.s.scalars(
            select(HealthConcern)
            .where(*visible_concerns())
            .order_by(HealthConcern.sort_order, HealthConcern.name)
        )
        return CatalogFilters(
            departments=[DepartmentOut.model_validate(d) for d in departments],
            categories=[CategoryOut.model_validate(c) for c in categories],
            sample_types=[SampleTypeOut.model_validate(s) for s in samples],
            concerns=[ConcernRef.model_validate(c) for c in concerns],
        )

    # ---------------------------------------------------------------- tests
    def _test_text_match(self, q: str) -> ColumnElement[bool]:
        conds: list[ColumnElement[bool]] = [
            func.lower(Test.name).like(_like(q), escape="\\"),
            func.lower(func.coalesce(Test.aliases, "")).like(_like(q), escape="\\"),
            nfc(Test.name_bn).like(_like(q), escape="\\"),
            func.lower(Test.code) == q,
            func.lower(Test.name).op("%")(q),
            # Typo tolerance against every word of the name and the aliases.
            literal(q, String).op("<%")(func.lower(Test.name)),
            literal(q, String).op("<%")(func.lower(func.coalesce(Test.aliases, ""))),
        ]
        tsq = prefix_tsquery(q)
        if tsq:
            conds.append(Test.search_vector.op("@@")(func.to_tsquery("simple", tsq)))
        return or_(*conds)

    async def list_tests(  # noqa: PLR0912 (one branch per optional filter)
        self, f: TestFilters, *, sort: TestSort, page: int, page_size: int
    ) -> tuple[list[TestSummary], int]:
        price = self.prices.amount_expr("TEST", Test.id)
        stmt = select(Test).where(*visible_tests())
        q = normalize_query(f.q) if f.q else ""
        if q:
            stmt = stmt.where(self._test_text_match(q))
        if f.department:
            stmt = stmt.join(Department, Department.id == Test.department_id).where(
                Department.code == f.department
            )
        if f.category:
            category_ids = select(Category.id).where(
                or_(
                    Category.slug == f.category,
                    Category.parent_id.in_(select(Category.id).where(Category.slug == f.category)),
                )
            )
            stmt = stmt.where(Test.category_id.in_(category_ids))
        if f.sample_type:
            stmt = stmt.join(SampleType, SampleType.id == Test.sample_type_id).where(
                SampleType.code == f.sample_type
            )
        if f.concern:
            stmt = stmt.where(
                Test.id.in_(
                    select(ConcernTest.test_id)
                    .join(HealthConcern, HealthConcern.id == ConcernTest.concern_id)
                    .where(HealthConcern.slug == f.concern)
                )
            )
        if f.home_collection is not None:
            stmt = stmt.where(Test.home_collection.is_(f.home_collection))
        if f.tat_max is not None:
            stmt = stmt.where(Test.tat_hours <= f.tat_max)
        if f.featured is not None:
            stmt = stmt.where(Test.is_featured.is_(f.featured))
        if f.price_min is not None:
            stmt = stmt.where(price >= f.price_min)
        if f.price_max is not None:
            stmt = stmt.where(price <= f.price_max)

        total = await self.s.scalar(select(func.count()).select_from(stmt.subquery()))
        order: list[Any]
        match sort:
            case "name":
                order = [Test.name]
            case "price_asc":
                order = [price.asc().nulls_last(), Test.name]
            case "price_desc":
                order = [price.desc().nulls_last(), Test.name]
            case "tat":
                order = [Test.tat_hours, Test.name]
            case "relevance" if q:
                order = [func.similarity(func.lower(Test.name), q).desc(), Test.popularity.desc()]
            case _:
                order = [Test.is_featured.desc(), Test.popularity.desc(), Test.name]
        rows = await self.s.scalars(
            stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)
        )
        return await self.reader.test_summaries(list(rows)), int(total or 0)

    async def get_test(self, slug: str) -> TestDetail:
        test = await self.s.scalar(select(Test).where(Test.slug == slug, *visible_tests()))
        if test is None:
            raise NotFound()
        summary = (await self.reader.test_summaries([test]))[0]
        category = await self.s.get(Category, test.category_id) if test.category_id else None
        preparation = (
            await self.s.get(Preparation, test.preparation_id) if test.preparation_id else None
        )
        parameters = await self.s.scalars(
            select(TestParameter)
            .where(TestParameter.test_id == test.id, TestParameter.is_active.is_(True))
            .order_by(TestParameter.display_order, TestParameter.name)
        )
        packages = await self.s.scalars(
            select(Package)
            .join(PackageTest, PackageTest.package_id == Package.id)
            .where(PackageTest.test_id == test.id, *visible_packages())
            .order_by(Package.popularity.desc(), Package.name)
            .limit(6)
        )
        return TestDetail(
            **summary.model_dump(),
            description=test.description,
            description_bn=test.description_bn,
            category=CategoryOut.model_validate(category) if category else None,
            sample_volume=test.sample_volume,
            preparation=PreparationOut.model_validate(preparation) if preparation else None,
            parameters=[
                ParameterPublic(code=p.code, name=p.name, name_bn=p.name_bn, unit=p.unit)
                for p in parameters
            ],
            concerns=await self.reader.concern_refs_for(test_id=test.id),
            packages=await self.reader.package_summaries(list(packages)),
            seo_title=test.seo_title,
            seo_description=test.seo_description,
            updated_at=test.updated_at,
        )

    # ---------------------------------------------------------------- packages
    async def list_packages(
        self, f: PackageFilters, *, sort: PackageSort, page: int, page_size: int
    ) -> tuple[list[PackageSummary], int]:
        price = self.prices.amount_expr("PACKAGE", Package.id)
        stmt = select(Package).where(*visible_packages())
        if f.q:
            q = normalize_query(f.q)
            stmt = stmt.where(
                or_(
                    func.lower(Package.name).like(_like(q), escape="\\"),
                    nfc(Package.name_bn).like(_like(q), escape="\\"),
                    func.lower(func.coalesce(Package.aliases, "")).like(_like(q), escape="\\"),
                )
            )
        if f.sex:
            # Unisex packages suit everyone.
            stmt = stmt.where(or_(Package.sex.is_(None), Package.sex == f.sex))
        if f.age is not None:
            stmt = stmt.where(
                or_(Package.age_min_years.is_(None), Package.age_min_years <= f.age),
                or_(Package.age_max_years.is_(None), Package.age_max_years >= f.age),
            )
        if f.concern:
            stmt = stmt.where(
                Package.id.in_(
                    select(ConcernPackage.package_id)
                    .join(HealthConcern, HealthConcern.id == ConcernPackage.concern_id)
                    .where(HealthConcern.slug == f.concern)
                )
            )
        if f.featured is not None:
            stmt = stmt.where(Package.is_featured.is_(f.featured))
        if f.price_min is not None:
            stmt = stmt.where(price >= f.price_min)
        if f.price_max is not None:
            stmt = stmt.where(price <= f.price_max)

        total = await self.s.scalar(select(func.count()).select_from(stmt.subquery()))
        order: list[Any]
        match sort:
            case "name":
                order = [Package.name]
            case "price_asc":
                order = [price.asc().nulls_last(), Package.name]
            case "price_desc":
                order = [price.desc().nulls_last(), Package.name]
            case _:
                order = [Package.is_featured.desc(), Package.popularity.desc(), Package.name]
        rows = await self.s.scalars(
            stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)
        )
        return await self.reader.package_summaries(list(rows)), int(total or 0)

    async def get_package(self, slug: str) -> PackageDetail:
        package = await self.s.scalar(
            select(Package).where(Package.slug == slug, *visible_packages())
        )
        if package is None:
            raise NotFound()
        summary = (await self.reader.package_summaries([package]))[0]
        tests = (await self.reader.package_tests([package.id])).get(package.id, [])
        prep_ids = {t.preparation_id for t in tests if t.preparation_id}
        preparations: Sequence[Preparation] = []
        if prep_ids:
            preparations = list(
                await self.s.scalars(
                    select(Preparation)
                    .where(Preparation.id.in_(prep_ids))
                    .order_by(Preparation.fasting_hours.desc().nulls_last())
                )
            )
        return PackageDetail(
            **summary.model_dump(exclude={"savings"}),
            description=package.description,
            description_bn=package.description_bn,
            tests=await self.reader.test_summaries(tests),
            concerns=await self.reader.concern_refs_for(package_id=package.id),
            preparations=[PreparationOut.model_validate(p) for p in preparations],
            seo_title=package.seo_title,
            seo_description=package.seo_description,
            updated_at=package.updated_at,
        )

    # ---------------------------------------------------------------- concerns
    async def list_concerns(self, *, featured: bool | None = None) -> list[ConcernSummary]:
        stmt = select(HealthConcern).where(*visible_concerns())
        if featured is not None:
            stmt = stmt.where(HealthConcern.is_featured.is_(featured))
        rows = await self.s.scalars(stmt.order_by(HealthConcern.sort_order, HealthConcern.name))
        return await self.reader.concern_summaries(list(rows))

    async def get_concern(self, slug: str) -> ConcernDetail:
        concern = await self.s.scalar(
            select(HealthConcern).where(HealthConcern.slug == slug, *visible_concerns())
        )
        if concern is None:
            raise NotFound()
        summary = (await self.reader.concern_summaries([concern]))[0]
        tests = await self.s.scalars(
            select(Test)
            .join(ConcernTest, ConcernTest.test_id == Test.id)
            .where(ConcernTest.concern_id == concern.id, *visible_tests())
            .order_by(Test.is_featured.desc(), Test.popularity.desc(), Test.name)
        )
        packages = await self.s.scalars(
            select(Package)
            .join(ConcernPackage, ConcernPackage.package_id == Package.id)
            .where(ConcernPackage.concern_id == concern.id, *visible_packages())
            .order_by(Package.is_featured.desc(), Package.popularity.desc(), Package.name)
        )
        return ConcernDetail(
            **summary.model_dump(),
            tests=await self.reader.test_summaries(list(tests)),
            packages=await self.reader.package_summaries(list(packages)),
            seo_title=concern.seo_title,
            seo_description=concern.seo_description,
            updated_at=concern.updated_at,
        )

    # ---------------------------------------------------------------- search
    async def _synonym_scores(self, q: str) -> dict[str, dict[uuid.UUID, float]]:
        """Synonym hits by target type. A hit on a concern also lifts that concern's tests
        and packages, so "sugar" (→ Diabetes) surfaces FBS, HbA1c and diabetes packages."""
        term = SearchSynonym.term
        qv = literal(q, String)
        exact = term == qv
        # Typing "sug" should find "sugar"; "blood sugar test" should find "blood sugar".
        prefix = func.strpos(term, qv) == 1
        contained = and_(func.length(term) >= 3, func.strpos(qv, term) > 0)
        fuzzy = term.op("%")(qv)
        scores = [
            case((exact, 1.0), else_=0.0),
            case((contained, 0.9), else_=0.0),
            cast(func.similarity(term, qv), Float),
        ]
        conditions = [exact, contained, fuzzy]
        if len(q) >= 3:
            scores.append(case((prefix, 0.85), else_=0.0))
            conditions.append(prefix)
        rows = await self.s.execute(
            select(
                SearchSynonym.target_type, SearchSynonym.target_id, func.greatest(*scores)
            ).where(or_(*conditions))
        )
        out: dict[str, dict[uuid.UUID, float]] = {"TEST": {}, "PACKAGE": {}, "CONCERN": {}}
        for target_type, target_id, s in rows:
            if s < 0.4:
                continue
            bucket = out[target_type]
            bucket[target_id] = max(bucket.get(target_id, 0.0), float(s))
        concerns = out["CONCERN"]
        if concerns:
            link_queries = (
                (
                    "TEST",
                    select(ConcernTest.concern_id, ConcernTest.test_id).where(
                        ConcernTest.concern_id.in_(concerns.keys())
                    ),
                ),
                (
                    "PACKAGE",
                    select(ConcernPackage.concern_id, ConcernPackage.package_id).where(
                        ConcernPackage.concern_id.in_(concerns.keys())
                    ),
                ),
            )
            for col, query in link_queries:
                for concern_id, target_id in await self.s.execute(query):
                    lifted = concerns[concern_id] * 0.7
                    bucket = out[col]
                    bucket[target_id] = max(bucket.get(target_id, 0.0), lifted)
        return out

    @staticmethod
    def _boost(col: Any, scores: dict[uuid.UUID, float]) -> ColumnElement[Any]:
        if not scores:
            return literal(0.0)
        return case({k: v * 2.0 for k, v in scores.items()}, value=col, else_=0.0)

    async def search(self, raw_q: str, *, limit: int, types: set[str]) -> SearchHits:
        q = normalize_query(raw_q)
        if not q:
            return SearchHits([], [], [])
        synonyms = await self._synonym_scores(q)
        tsq = prefix_tsquery(q)
        tsquery = func.to_tsquery("simple", tsq) if tsq else None
        tests: list[TestSummary] = []
        packages: list[PackageSummary] = []
        concerns: list[ConcernSummary] = []

        if "test" in types:
            rank = func.ts_rank_cd(Test.search_vector, tsquery) if tsquery is not None else 0.0
            score = (
                rank * 2
                + func.greatest(
                    func.similarity(func.lower(Test.name), q),
                    func.word_similarity(q, func.lower(Test.name)),
                    func.word_similarity(q, func.lower(func.coalesce(Test.aliases, ""))) * 0.8,
                )
                + case((func.lower(Test.code) == q, 3.0), else_=0.0)
                + case(
                    (func.lower(Test.name).like(f"{escape_like(q)}%", escape="\\"), 0.5), else_=0.0
                )
                + self._boost(Test.id, synonyms["TEST"])
                + Test.popularity * 0.0001
            )
            match = self._test_text_match(q)
            if synonyms["TEST"]:
                match = or_(match, Test.id.in_(synonyms["TEST"].keys()))
            rows = await self.s.scalars(
                select(Test)
                .where(*visible_tests(), match)
                .order_by(score.desc(), Test.name)
                .limit(limit)
            )
            tests = await self.reader.test_summaries(list(rows))

        if "package" in types:
            conds: list[ColumnElement[bool]] = [
                func.lower(Package.name).like(_like(q), escape="\\"),
                nfc(Package.name_bn).like(_like(q), escape="\\"),
                func.lower(func.coalesce(Package.aliases, "")).like(_like(q), escape="\\"),
                func.lower(Package.name).op("%")(q),
            ]
            if tsquery is not None:
                conds.append(Package.search_vector.op("@@")(tsquery))
            if synonyms["PACKAGE"]:
                conds.append(Package.id.in_(synonyms["PACKAGE"].keys()))
            rank = func.ts_rank_cd(Package.search_vector, tsquery) if tsquery is not None else 0.0
            score = (
                rank * 2
                + func.similarity(func.lower(Package.name), q)
                + self._boost(Package.id, synonyms["PACKAGE"])
                + Package.popularity * 0.0001
            )
            rows_p = await self.s.scalars(
                select(Package)
                .where(*visible_packages(), or_(*conds))
                .order_by(score.desc(), Package.name)
                .limit(limit)
            )
            packages = await self.reader.package_summaries(list(rows_p))

        if "concern" in types:
            conds = [
                func.lower(HealthConcern.name).like(_like(q), escape="\\"),
                nfc(HealthConcern.name_bn).like(_like(q), escape="\\"),
                func.lower(HealthConcern.name).op("%")(q),
            ]
            if tsquery is not None:
                conds.append(HealthConcern.search_vector.op("@@")(tsquery))
            if synonyms["CONCERN"]:
                conds.append(HealthConcern.id.in_(synonyms["CONCERN"].keys()))
            score = func.similarity(func.lower(HealthConcern.name), q) + self._boost(
                HealthConcern.id, synonyms["CONCERN"]
            )
            rows_c = await self.s.scalars(
                select(HealthConcern)
                .where(*visible_concerns(), or_(*conds))
                .order_by(score.desc(), HealthConcern.name)
                .limit(limit)
            )
            concerns = await self.reader.concern_summaries(list(rows_c))

        return SearchHits(tests, packages, concerns)

    # ---------------------------------------------------------------- sitemap
    async def sitemap_entries(self) -> list[tuple[str, str, datetime]]:
        out: list[tuple[str, str, datetime]] = []
        for kind, model, where in (
            ("test", Test, visible_tests()),
            ("package", Package, visible_packages()),
            ("concern", HealthConcern, visible_concerns()),
        ):
            rows = await self.s.execute(select(model.slug, model.updated_at).where(*where))
            out.extend((kind, slug, updated) for slug, updated in rows)
        return out


async def item_names(
    session: AsyncSession, item_type: str, ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Names for price/booking snapshots and admin labels."""
    model: Any = Test if item_type == "TEST" else Package
    rows = await session.execute(select(model.id, model.name).where(model.id.in_(set(ids))))
    return dict(rows.all())
