"""Catalogue seeding.

`seed_catalog_base` runs everywhere: it guarantees the default price list exists.
`seed_catalog_demo` (development/test only) loads the clearly labelled DEMO catalogue,
centres and CMS content from `demo_catalog`. Both are idempotent and never overwrite rows
that already exist, so edits made in the console survive re-seeding.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text import normalize_query
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
from app.modules.centre.models import Branch, Centre, CentreHours, Holiday, Lab
from app.modules.cms.models import Banner, Faq, Page
from app.modules.geo.models import Area, District, Upazila
from app.scripts import demo_catalog as demo

DEFAULT_PRICE_LIST = "DEFAULT"


async def seed_catalog_base(session: AsyncSession) -> PriceList:
    pl = await session.scalar(select(PriceList).where(PriceList.branch_id.is_(None)))
    if pl is None:
        pl = PriceList(code=DEFAULT_PRICE_LIST, name="Standard prices")
        session.add(pl)
        await session.flush()
    return pl


async def _get_or_create(
    session: AsyncSession, model: Any, key: str, value: str, **fields: Any
) -> Any:
    row = await session.scalar(select(model).where(getattr(model, key) == value))
    if row is None:
        row = model(**{key: value}, **fields)
        session.add(row)
        await session.flush()
    return row


async def _price(
    session: AsyncSession, pl: PriceList, item_type: str, item_id: uuid.UUID, price: int, mrp: int
) -> None:
    ref = PriceListItem.test_id if item_type == "TEST" else PriceListItem.package_id
    exists = await session.scalar(
        select(func.count())
        .select_from(PriceListItem)
        .where(PriceListItem.price_list_id == pl.id, ref == item_id)
    )
    if not exists:
        session.add(
            PriceListItem(
                price_list_id=pl.id,
                item_type=item_type,
                test_id=item_id if item_type == "TEST" else None,
                package_id=item_id if item_type == "PACKAGE" else None,
                price=price * 100,
                mrp=mrp * 100,
            )
        )


async def _seed_tests(session: AsyncSession, pl: PriceList) -> dict[str, Test]:
    departments = {
        code: await _get_or_create(
            session, Department, "code", code, name=name, name_bn=bn, sort_order=order
        )
        for code, name, bn, order in demo.DEPARTMENTS
    }
    categories: dict[str, Category] = {}
    for slug, name, bn, parent in demo.CATEGORIES:
        categories[slug] = await _get_or_create(
            session,
            Category,
            "slug",
            slug,
            name=name,
            name_bn=bn,
            parent_id=categories[parent].id if parent else None,
        )
    samples = {
        code: await _get_or_create(
            session,
            SampleType,
            "code",
            code,
            name=name,
            name_bn=bn,
            container=container,
            tube_colour=colour,
            default_volume_ml=Decimal(ml) if ml else None,
        )
        for code, (name, bn, container, colour, ml) in demo.SAMPLE_TYPES.items()
    }
    preps = {
        code: await _get_or_create(
            session,
            Preparation,
            "code",
            code,
            title=title,
            title_bn=title_bn,
            instructions=instr,
            instructions_bn=instr_bn,
            fasting_hours=hours,
        )
        for code, (title, title_bn, instr, instr_bn, hours) in demo.PREPARATIONS.items()
    }

    tests: dict[str, Test] = {}
    for code, t in demo.TESTS.items():
        test = await session.scalar(select(Test).where(Test.code == code))
        if test is None:
            test = Test(
                code=code,
                slug=code.lower().replace("_", "-"),
                name=t["name"],
                name_bn=t["name_bn"],
                aliases=t.get("aliases"),
                short_description=t.get("short"),
                short_description_bn=t.get("short_bn"),
                description=t.get("short"),
                description_bn=t.get("short_bn"),
                department_id=departments[t["dept"]].id,
                category_id=categories[t["cat"]].id,
                sample_type_id=samples[t["sample"]].id,
                preparation_id=preps[t["prep"]].id if t.get("prep") else None,
                tat_hours=t["tat"],
                home_collection=t.get("home", True),
                is_featured=t.get("featured", False),
                popularity=t.get("pop", 0),
            )
            session.add(test)
            await session.flush()
            for order, (
                pcode,
                pname,
                pname_bn,
                unit,
                rtype,
                decimals,
                ranges,
                options,
            ) in enumerate(t["params"]):
                param = TestParameter(
                    test_id=test.id,
                    code=pcode,
                    name=pname,
                    name_bn=pname_bn,
                    unit=unit,
                    result_type=rtype,
                    decimals=decimals,
                    options=options,
                    display_order=order,
                )
                session.add(param)
                await session.flush()
                for sex, low, high, cl, ch, normal in ranges:
                    session.add(
                        ReferenceRange(
                            parameter_id=param.id,
                            sex=sex,
                            age_min_days=18 * 365,
                            low=_dec(low),
                            high=_dec(high),
                            critical_low=_dec(cl),
                            critical_high=_dec(ch),
                            text_normal=normal,
                            effective_from=date(2020, 1, 1),
                            notes=demo.DEMO_NOTE,
                        )
                    )
        await _price(session, pl, "TEST", test.id, t["price"], t["mrp"])
        tests[code] = test
    await session.flush()
    return tests


def _dec(v: float | None) -> Decimal | None:
    return Decimal(str(v)) if v is not None else None


async def _seed_packages_and_concerns(
    session: AsyncSession, pl: PriceList, tests: dict[str, Test]
) -> None:
    packages: dict[str, Package] = {}
    for slug, (
        name,
        bn,
        short,
        short_bn,
        codes,
        price,
        mrp,
        sex,
        amin,
        amax,
        featured,
        pop,
    ) in demo.PACKAGES.items():
        package = await session.scalar(select(Package).where(Package.slug == slug))
        if package is None:
            package = Package(
                code=slug.upper().replace("-", "_")[:40],
                slug=slug,
                name=name,
                name_bn=bn,
                short_description=short,
                short_description_bn=short_bn,
                description=short,
                description_bn=short_bn,
                sex=sex,
                age_min_years=amin,
                age_max_years=amax,
                is_featured=featured,
                popularity=pop,
            )
            session.add(package)
            await session.flush()
            session.add_all(
                PackageTest(package_id=package.id, test_id=tests[c].id, sort_order=i)
                for i, c in enumerate(codes)
            )
        await _price(session, pl, "PACKAGE", package.id, price, mrp)
        packages[slug] = package
    await session.flush()

    concerns: dict[str, HealthConcern] = {}
    for slug, (
        name,
        bn,
        icon,
        desc,
        desc_bn,
        codes,
        pkgs,
        featured,
        order,
    ) in demo.CONCERNS.items():
        concern = await session.scalar(select(HealthConcern).where(HealthConcern.slug == slug))
        if concern is None:
            concern = HealthConcern(
                slug=slug,
                name=name,
                name_bn=bn,
                icon=icon,
                description=desc,
                description_bn=desc_bn,
                is_featured=featured,
                sort_order=order,
            )
            session.add(concern)
            await session.flush()
            session.add_all(ConcernTest(concern_id=concern.id, test_id=tests[c].id) for c in codes)
            session.add_all(
                ConcernPackage(concern_id=concern.id, package_id=packages[p].id) for p in pkgs
            )
        concerns[slug] = concern
    await session.flush()

    targets: dict[str, dict[str, Any]] = {"TEST": tests, "PACKAGE": packages, "CONCERN": concerns}
    for term, refs in demo.SYNONYMS.items():
        normalized = normalize_query(term)
        for target_type, key in refs:
            target_id = targets[target_type][key].id
            exists = await session.scalar(
                select(func.count())
                .select_from(SearchSynonym)
                .where(
                    SearchSynonym.term == normalized,
                    SearchSynonym.target_type == target_type,
                    SearchSynonym.target_id == target_id,
                )
            )
            if not exists:
                session.add(
                    SearchSynonym(term=normalized, target_type=target_type, target_id=target_id)
                )
    await session.flush()


async def _seed_centres(session: AsyncSession) -> None:
    code, name, bn = demo.BRANCH
    branch = await _get_or_create(session, Branch, "code", code, name=name, name_bn=bn)
    lab_code, lab_name, lab_bn = demo.LAB
    lab = await _get_or_create(
        session, Lab, "code", lab_code, name=lab_name, name_bn=lab_bn, branch_id=branch.id
    )

    # Saturday-Thursday 07:00-21:00, Friday 15:00-21:00 (weekday 0 = Monday).
    week = [(d, time(7), time(21)) for d in (5, 6, 0, 1, 2, 3)] + [(4, time(15), time(21))]
    for (
        c_code,
        slug,
        c_name,
        c_bn,
        c_type,
        district,
        upazila,
        area,
        address,
        address_bn,
        landmark,
        lat,
        lng,
        phone,
        services,
    ) in demo.CENTRES:
        if await session.scalar(select(Centre).where(Centre.code == c_code)) is not None:
            continue
        district_row = await session.scalar(select(District).where(District.name == district))
        assert district_row is not None, district
        upazila_row = await session.scalar(
            select(Upazila).where(Upazila.district_id == district_row.id, Upazila.name == upazila)
        )
        area_row = (
            await session.scalar(
                select(Area).where(Area.upazila_id == upazila_row.id, Area.name == area)
            )
            if upazila_row
            else None
        )
        session.add(
            Centre(
                code=c_code,
                slug=slug,
                name=c_name,
                name_bn=c_bn,
                type=c_type,
                branch_id=branch.id,
                lab_id=lab.id,
                address=address,
                address_bn=address_bn,
                landmark=landmark,
                district_id=district_row.id,
                upazila_id=upazila_row.id if upazila_row else None,
                area_id=area_row.id if area_row else None,
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lng)),
                phone=f"+880{phone[1:]}",
                services=sorted(services),
                description="DEMO centre for development and demonstrations.",
                description_bn="উন্নয়ন ও প্রদর্শনের জন্য ডেমো কেন্দ্র।",
                hours=[CentreHours(weekday=d, opens_at=o, closes_at=c) for d, o, c in week],
            )
        )
    for day, h_name, h_bn in demo.HOLIDAYS_2026:
        on = date.fromisoformat(day)
        exists = await session.scalar(
            select(func.count())
            .select_from(Holiday)
            .where(Holiday.branch_id == branch.id, Holiday.date == on)
        )
        if not exists:
            session.add(Holiday(branch_id=branch.id, date=on, name=h_name, name_bn=h_bn))
    await session.flush()


async def _seed_cms(session: AsyncSession) -> None:
    if not await session.scalar(select(func.count()).select_from(Banner)):
        session.add_all(Banner(status="PUBLISHED", **b) for b in demo.BANNERS)
    for page in demo.PAGES:
        if await session.scalar(select(Page).where(Page.slug == page["slug"])) is None:
            session.add(Page(status="PUBLISHED", **page))
    if not await session.scalar(select(func.count()).select_from(Faq)):
        session.add_all(
            Faq(
                status="PUBLISHED",
                category=cat,
                question=q,
                question_bn=q_bn,
                answer=a,
                answer_bn=a_bn,
                sort_order=i,
            )
            for i, (cat, q, q_bn, a, a_bn) in enumerate(demo.FAQS)
        )
    await session.flush()


async def seed_catalog_demo(session: AsyncSession) -> dict[str, int]:
    pl = await seed_catalog_base(session)
    tests = await _seed_tests(session, pl)
    await _seed_packages_and_concerns(session, pl, tests)
    await _seed_centres(session)
    await _seed_cms(session)
    counts = {}
    for label, model in (
        ("tests", Test),
        ("packages", Package),
        ("concerns", HealthConcern),
        ("synonyms", SearchSynonym),
        ("centres", Centre),
        ("price rows", PriceListItem),
    ):
        counts[label] = int(await session.scalar(select(func.count()).select_from(model)) or 0)
    return counts
