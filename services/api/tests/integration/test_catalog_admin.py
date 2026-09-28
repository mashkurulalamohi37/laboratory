"""Catalogue administration: RBAC, audit, optimistic locking, reference-range and pricing
guard rails, against real PostgreSQL + Redis."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy.exc import DBAPIError

from app.modules.auth.permissions import Role
from tests.integration.conftest import db_execute, db_scalar, patient_login, staff_headers

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("demo_catalog")]

API = "/api/v1/admin/catalog"
ADMIN = "+8801911100001"
TECH = "+8801911100002"
ACCOUNTANT = "+8801911100003"
CONTENT = "+8801911100004"


async def _ids(client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, str]:
    """Department and sample type IDs for building test payloads."""
    departments = (await client.get(f"{API}/departments", headers=headers)).json()["data"]
    samples = (await client.get(f"{API}/sample-types", headers=headers)).json()["data"]
    return {
        "department_id": next(d["id"] for d in departments if d["code"] == "BIOCHEM"),
        "sample_type_id": next(s["id"] for s in samples if s["code"] == "SERUM"),
    }


async def _test_id(code: str) -> str:
    return str(await db_scalar("SELECT id FROM catalog.tests WHERE code = :c", c=code))


def _new_test(ids: dict[str, str], code: str = "MAG") -> dict[str, Any]:
    return {
        "code": code,
        "slug": code.lower(),
        "name": "Serum Magnesium",
        "name_bn": "সিরাম ম্যাগনেসিয়াম",
        "tat_hours": 24,
        **ids,
    }


async def test_permissions(client: httpx.AsyncClient) -> None:
    patient = await patient_login(client)
    assert (await client.get(f"{API}/tests", headers=patient.headers)).status_code == 403

    tech = await staff_headers(client, TECH, Role.LAB_TECHNICIAN)
    assert (await client.get(f"{API}/tests", headers=tech)).status_code == 200  # test:view
    ids = await _ids(client, tech)
    res = await client.post(f"{API}/tests", headers=tech, json=_new_test(ids))
    assert res.status_code == 403  # no test:create
    res = await client.get(f"{API}/price-lists", headers=tech)
    assert res.status_code == 200
    pl = res.json()["data"][0]["id"]
    res = await client.put(
        f"{API}/price-lists/{pl}/items",
        headers=tech,
        json={"item_type": "TEST", "item_id": await _test_id("CBC"), "mrp": 1, "price": 1},
    )
    assert res.status_code == 403  # no price:manage

    accountant = await staff_headers(client, ACCOUNTANT, Role.ACCOUNTANT)
    assert (await client.get(f"{API}/price-lists", headers=accountant)).status_code == 200


async def test_create_update_delete_test_with_audit_and_version(client: httpx.AsyncClient) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    ids = await _ids(client, admin)

    res = await client.post(f"{API}/tests", headers=admin, json=_new_test(ids))
    assert res.status_code == 201, res.text
    test = res.json()["data"]
    assert test["version"] == 1 and test["parameters"] == [] and test["prices"] == []

    dup = await client.post(f"{API}/tests", headers=admin, json=_new_test(ids))
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE"

    bad = await client.post(
        f"{API}/tests", headers=admin, json={**_new_test(ids, "X1"), "department_id": test["id"]}
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["details"][0]["field"] == "department_id"

    res = await client.patch(
        f"{API}/tests/{test['id']}",
        headers={**admin, "If-Match": "1"},
        json={"name": "Serum Magnesium (Mg)", "is_featured": True},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["version"] == 2

    stale = await client.patch(
        f"{API}/tests/{test['id']}", headers={**admin, "If-Match": "1"}, json={"name": "Stale"}
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "VERSION_CONFLICT"

    audit = await db_scalar(
        "SELECT count(*) FROM audit.audit_logs WHERE entity_type = 'test' AND entity_id = :i",
        i=test["id"],
    )
    assert audit == 2  # created + updated (the stale edit was rolled back)

    res = await client.delete(f"{API}/tests/{test['id']}", headers=admin)
    assert res.status_code == 204
    assert (await client.get(f"{API}/tests/{test['id']}", headers=admin)).status_code == 404


async def test_test_in_active_package_cannot_be_deleted_or_deactivated(
    client: httpx.AsyncClient,
) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    cbc = await _test_id("CBC")
    res = await client.delete(f"{API}/tests/{cbc}", headers=admin)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "TEST_IN_ACTIVE_PACKAGES"
    res = await client.patch(f"{API}/tests/{cbc}", headers=admin, json={"is_active": False})
    assert res.status_code == 422


async def test_parameters_and_reference_ranges(client: httpx.AsyncClient) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    ids = await _ids(client, admin)
    test = (await client.post(f"{API}/tests", headers=admin, json=_new_test(ids))).json()["data"]

    res = await client.post(
        f"{API}/tests/{test['id']}/parameters",
        headers=admin,
        json={"code": "MG", "name": "Magnesium", "unit": "mg/dL", "decimals": 2},
    )
    assert res.status_code == 201, res.text
    param = res.json()["data"]["parameters"][0]

    calc = await client.post(
        f"{API}/tests/{test['id']}/parameters",
        headers=admin,
        json={"code": "X", "name": "X", "result_type": "CALCULATED"},
    )
    assert calc.status_code == 400  # CALCULATED needs a formula

    adult = {"age_min_days": 6570, "low": "1.7", "high": "2.2", "critical_low": "1.0"}
    res = await client.post(
        f"{API}/parameters/{param['id']}/reference-ranges", headers=admin, json=adult
    )
    assert res.status_code == 201, res.text

    child = {"age_min_days": 365, "age_max_days": 6570, "low": "1.5", "high": "2.3"}
    res = await client.post(
        f"{API}/parameters/{param['id']}/reference-ranges", headers=admin, json=child
    )
    assert res.status_code == 201, res.text  # adjacent bands are fine

    overlap = {"age_min_days": 5000, "low": "1.6", "high": "2.4"}
    res = await client.post(
        f"{API}/parameters/{param['id']}/reference-ranges", headers=admin, json=overlap
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "REFERENCE_RANGE_OVERLAP"

    male = {**overlap, "sex": "M"}  # different criteria: allowed
    res = await client.post(
        f"{API}/parameters/{param['id']}/reference-ranges", headers=admin, json=male
    )
    assert res.status_code == 201, res.text

    invalid = {"low": "3", "high": "2"}
    res = await client.post(
        f"{API}/parameters/{param['id']}/reference-ranges", headers=admin, json=invalid
    )
    assert res.status_code == 400

    detail = (await client.get(f"{API}/tests/{test['id']}", headers=admin)).json()["data"]
    assert len(detail["parameters"][0]["ranges"]) == 3


async def test_database_rejects_overlapping_ranges_even_without_the_api() -> None:
    param = await db_scalar(
        "SELECT p.id FROM catalog.test_parameters p JOIN catalog.tests t ON t.id = p.test_id "
        "WHERE t.code = 'FBS'"
    )
    with pytest.raises(DBAPIError, match="ex_reference_ranges_no_overlap"):
        await db_execute(
            "INSERT INTO catalog.reference_ranges (id, parameter_id, age_min_days, low, high) "
            "VALUES (gen_random_uuid(), :p, 20000, 1, 2)",
            p=param,
        )


async def test_price_changes_keep_history_and_support_scheduling(
    client: httpx.AsyncClient,
) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    lists = (await client.get(f"{API}/price-lists", headers=admin)).json()["data"]
    default = next(pl for pl in lists if pl["branch_id"] is None)
    cbc = await _test_id("CBC")
    url = f"{API}/price-lists/{default['id']}/items"

    res = await client.put(
        url, headers=admin, json={"item_type": "TEST", "item_id": cbc, "mrp": 50000, "price": 45000}
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["current"]["amount"] == 45000

    later = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    res = await client.put(
        url,
        headers=admin,
        json={
            "item_type": "TEST",
            "item_id": cbc,
            "mrp": 50000,
            "price": 42000,
            "effective_from": later,
        },
    )
    assert res.status_code == 200, res.text
    item = res.json()["data"]
    assert item["current"]["amount"] == 45000 and item["scheduled"]["amount"] == 42000

    public = (await client.get("/api/v1/tests/cbc")).json()["data"]
    assert public["price"]["amount"] == 45000  # the scheduled price is not live yet

    history = (await client.get(f"{url}/TEST/{cbc}/history", headers=admin)).json()["data"]
    assert [h["price"]["amount"] for h in history] == [42000, 45000, 40000]
    assert history[2]["effective_to"] is not None  # the seed price was closed, not rewritten

    bad = await client.put(
        url, headers=admin, json={"item_type": "TEST", "item_id": cbc, "mrp": 100, "price": 200}
    )
    assert bad.status_code == 400
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    bad = await client.put(
        url,
        headers=admin,
        json={"item_type": "TEST", "item_id": cbc, "mrp": 100, "price": 50, "effective_from": past},
    )
    assert bad.status_code == 400

    res = await client.delete(f"{url}/TEST/{cbc}", headers=admin)
    assert res.status_code == 204
    assert (await client.get("/api/v1/tests/cbc")).json()["data"]["price"] is None


async def test_default_price_list_cannot_be_deactivated(client: httpx.AsyncClient) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    lists = (await client.get(f"{API}/price-lists", headers=admin)).json()["data"]
    default = next(pl for pl in lists if pl["branch_id"] is None)
    res = await client.patch(
        f"{API}/price-lists/{default['id']}", headers=admin, json={"is_active": False}
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "DEFAULT_PRICE_LIST_REQUIRED"


async def test_package_management(client: httpx.AsyncClient) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    tests = [await _test_id(c) for c in ("CBC", "FBS", "TSH")]
    res = await client.post(
        f"{API}/packages",
        headers=admin,
        json={"code": "STARTER", "slug": "starter", "name": "Starter check", "test_ids": tests},
    )
    assert res.status_code == 201, res.text
    package = res.json()["data"]
    assert package["test_ids"] == tests and package["tests_total"] == 125_000

    res = await client.patch(
        f"{API}/packages/{package['id']}",
        headers={**admin, "If-Match": str(package["version"])},
        json={"test_ids": tests[:2]},
    )
    assert res.status_code == 200 and res.json()["data"]["test_ids"] == tests[:2]

    res = await client.post(
        f"{API}/packages",
        headers=admin,
        json={"code": "EMPTY", "slug": "empty", "name": "Empty", "test_ids": []},
    )
    assert res.status_code == 400


async def test_synonyms_drive_search_and_invalidate_cache(client: httpx.AsyncClient) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    urid = await _test_id("URIC")
    primed = await client.get("/api/v1/search/autocomplete", params={"q": "joint pain"})
    assert "uric" not in [s["slug"] for s in primed.json()["data"]]  # now cached
    res = await client.post(
        f"{API}/synonyms",
        headers=admin,
        json={"term": "  Joint Pain ", "target_type": "TEST", "target_id": urid},
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["term"] == "joint pain"
    after = (await client.get("/api/v1/search/autocomplete", params={"q": "joint pain"})).json()
    assert "uric" in [s["slug"] for s in after["data"]]

    bad = await client.post(
        f"{API}/synonyms",
        headers=admin,
        json={"term": "<script>", "target_type": "TEST", "target_id": urid},
    )
    assert bad.status_code == 400


async def test_content_manager_cannot_edit_catalogue(client: httpx.AsyncClient) -> None:
    content = await staff_headers(client, CONTENT, Role.CONTENT_MANAGER)
    ids = await _ids(client, content)
    assert (
        await client.post(f"{API}/tests", headers=content, json=_new_test(ids))
    ).status_code == 403
