"""Public catalogue, search and SEO feed against real PostgreSQL + Redis (DEMO data)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.integration.conftest import db_execute, db_scalar

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("demo_catalog")]

API = "/api/v1"


async def _get(client: httpx.AsyncClient, url: str, **params: Any) -> Any:
    res = await client.get(f"{API}{url}", params=params)
    assert res.status_code == 200, res.text
    return res.json()


def _codes(items: list[dict[str, Any]]) -> list[str]:
    return [i["code"] for i in items]


async def test_exit_demo_sugar_finds_fbs_hba1c_and_diabetes_package(
    client: httpx.AsyncClient,
) -> None:
    data = (await _get(client, "/search", q="sugar"))["data"]
    tests = _codes(data["tests"])
    assert {"FBS", "HBA1C"} <= set(tests)
    assert "diabetes-screening" in [p["slug"] for p in data["packages"]]
    assert data["concerns"][0]["slug"] == "diabetes"


@pytest.mark.parametrize(
    ("query", "expected_code"),
    [
        ("সুগার", "FBS"),  # Bangla synonym
        ("ডেঙ্গু", "DENGUE_NS1"),  # Bangla synonym to a test
        ("hemoglobn", "CBC"),  # typo against an alias
        ("platelete", "CBC"),
        ("cholestrol", "LIPID"),
        ("cbc", "CBC"),  # exact code
        ("vitamin d", "VITD"),
    ],
)
async def test_search_handles_bangla_typos_and_codes(
    client: httpx.AsyncClient, query: str, expected_code: str
) -> None:
    data = (await _get(client, "/search", q=query, types="test"))["data"]
    assert expected_code in _codes(data["tests"])[:3], (query, _codes(data["tests"]))


async def test_search_is_injection_safe(client: httpx.AsyncClient) -> None:
    for q in ["sugar' OR 1=1 --", "a & b | !c", "100%_", "):*"]:
        res = await client.get(f"{API}/search", params={"q": q})
        assert res.status_code == 200, (q, res.text)


async def test_search_validates_types(client: httpx.AsyncClient) -> None:
    res = await client.get(f"{API}/search", params={"q": "x", "types": "test,users"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_autocomplete_is_cached_and_invalidated_by_catalog_changes(
    client: httpx.AsyncClient,
) -> None:
    first = (await _get(client, "/search/autocomplete", q="thyr"))["data"]
    assert ("concern", "thyroid") in [(s["type"], s["slug"]) for s in first]
    # A change written behind the API's back is invisible while the cache holds...
    await db_execute("UPDATE catalog.health_concerns SET is_active = false WHERE slug = 'thyroid'")
    cached = (await _get(client, "/search/autocomplete", q="thyr"))["data"]
    assert cached == first
    # ...and a real catalogue change (through the service) bumps the cache version.
    from app.core.cache import SEARCH_NAMESPACE, bump_namespace

    await bump_namespace(SEARCH_NAMESPACE)
    fresh = (await _get(client, "/search/autocomplete", q="thyr"))["data"]
    assert ("concern", "thyroid") not in [(s["type"], s["slug"]) for s in fresh]


async def test_test_list_filters_and_sorting(client: httpx.AsyncClient) -> None:
    body = await _get(client, "/tests", concern="diabetes", sort="price_asc", page_size=50)
    prices = [t["price"]["amount"] for t in body["data"]]
    assert prices == sorted(prices)
    assert set(_codes(body["data"])) == {"FBS", "RBS", "2HABF", "OGTT", "HBA1C"}
    assert body["meta"]["total"] == 5

    cheap = (await _get(client, "/tests", price_max=20_000, page_size=100))["data"]
    assert cheap and all(t["price"]["amount"] <= 20_000 for t in cheap)

    haem = (await _get(client, "/tests", department="HAEM"))["data"]
    assert haem and {t["department"]["code"] for t in haem} == {"HAEM"}

    # Category filter includes child categories.
    blood = (await _get(client, "/tests", category="blood-tests", page_size=100))["meta"]["total"]
    diabetes = (await _get(client, "/tests", category="diabetes-tests"))["meta"]["total"]
    assert blood > diabetes > 0

    centre_only = (await _get(client, "/tests", home_collection="false"))["data"]
    assert _codes(centre_only) == ["OGTT"]


async def test_test_detail(client: httpx.AsyncClient) -> None:
    test = (await _get(client, "/tests/fbs"))["data"]
    assert test["preparation"]["fasting_hours"] == 8
    assert test["price"] == {
        "amount": 15000,
        "mrp": 20000,
        "currency": "BDT",
        "discount_percent": 25,
    }
    assert [p["code"] for p in test["parameters"]] == ["GLU_F"]
    assert "diabetes" in [c["slug"] for c in test["concerns"]]
    assert "diabetes-screening" in [p["slug"] for p in test["packages"]]
    # Reference ranges are staff-only data.
    assert "ranges" not in test["parameters"][0]


async def test_inactive_and_deleted_items_are_hidden(client: httpx.AsyncClient) -> None:
    await db_execute("UPDATE catalog.tests SET is_active = false WHERE code = 'PSA'")
    await db_execute("UPDATE catalog.tests SET deleted_at = now() WHERE code = 'BHCG'")
    assert (await client.get(f"{API}/tests/psa")).status_code == 404
    assert (await client.get(f"{API}/tests/bhcg")).status_code == 404
    codes = _codes((await _get(client, "/tests", page_size=100))["data"])
    assert "PSA" not in codes and "BHCG" not in codes
    # Packages list only their visible tests.
    mens = (await _get(client, "/packages/mens-health"))["data"]
    assert "PSA" not in _codes(mens["tests"])


async def test_package_pricing_and_savings(client: httpx.AsyncClient) -> None:
    package = (await _get(client, "/packages/basic-health-checkup"))["data"]
    individual = sum(t["price"]["amount"] for t in package["tests"])
    assert package["tests_total"] == individual == 310_000
    assert package["price"]["amount"] == 220_000
    assert package["savings"] == 90_000
    assert package["fasting_hours"] == 10  # the longest fast among its tests
    assert package["test_count"] == 7


async def test_package_targeting(client: httpx.AsyncClient) -> None:
    for_women = [
        p["slug"] for p in (await _get(client, "/packages", sex="F", age=30, page_size=50))["data"]
    ]
    assert "womens-health" in for_women
    assert "mens-health" not in for_women  # male-only
    assert "senior-citizen-checkup" not in for_women  # 60+
    seniors = [p["slug"] for p in (await _get(client, "/packages", age=65, page_size=50))["data"]]
    assert "senior-citizen-checkup" in seniors


async def test_unpriced_items_show_null_price_and_branch_lists_override(
    client: httpx.AsyncClient,
) -> None:
    await db_execute(
        "UPDATE catalog.price_list_items SET effective_to = now() "
        "WHERE test_id = (SELECT id FROM catalog.tests WHERE code = 'ESR')"
    )
    esr = (await _get(client, "/tests/esr"))["data"]
    assert esr["price"] is None

    branch_id = await db_scalar("SELECT id FROM centre.branches WHERE code = 'DHAKA'")
    await db_execute(
        "INSERT INTO catalog.price_lists (id, code, name, branch_id) "
        "VALUES (gen_random_uuid(), 'DHAKA', 'Dhaka prices', :b)",
        b=branch_id,
    )
    await db_execute(
        "INSERT INTO catalog.price_list_items (id, price_list_id, item_type, test_id, mrp, price) "
        "SELECT gen_random_uuid(), pl.id, 'TEST', t.id, 20000, 12000 "
        "FROM catalog.price_lists pl, catalog.tests t WHERE pl.code = 'DHAKA' AND t.code = 'FBS'"
    )
    default = (await _get(client, "/tests/fbs"))["data"]["price"]["amount"]
    branch = (await _get(client, "/tests/fbs", branch_id=str(branch_id)))["data"]["price"]["amount"]
    fallback = (await _get(client, "/tests/rbs", branch_id=str(branch_id)))["data"]["price"][
        "amount"
    ]
    assert (default, branch, fallback) == (15_000, 12_000, 15_000)


async def test_concerns_and_filters(client: httpx.AsyncClient) -> None:
    concerns = (await _get(client, "/health-concerns", featured="true"))["data"]
    diabetes = next(c for c in concerns if c["slug"] == "diabetes")
    assert diabetes["test_count"] == 5 and diabetes["package_count"] == 2
    detail = (await _get(client, "/health-concerns/diabetes"))["data"]
    assert len(detail["tests"]) == 5 and len(detail["packages"]) == 2

    facets = (await _get(client, "/catalog/filters"))["data"]
    assert {d["code"] for d in facets["departments"]} >= {"HAEM", "BIOCHEM"}
    assert any(s["code"] == "EDTA_WB" for s in facets["sample_types"])


async def test_public_reads_are_cacheable(client: httpx.AsyncClient) -> None:
    res = await client.get(f"{API}/tests")
    assert res.headers["cache-control"].startswith("public, max-age=")


async def test_sitemap_lists_public_urls(client: httpx.AsyncClient) -> None:
    entries = (await _get(client, "/seo/sitemap"))["data"]
    kinds = {(e["type"], e["slug"]) for e in entries}
    assert ("test", "cbc") in kinds
    assert ("package", "basic-health-checkup") in kinds
    assert ("concern", "diabetes") in kinds
    assert ("centre", "gulshan") in kinds
    assert ("page", "about") in kinds
