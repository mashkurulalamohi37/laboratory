"""Centres, geography, CMS publishing and RBAC scope validation (real PostgreSQL + Redis)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from app.modules.auth.permissions import Role
from tests.integration.conftest import db_scalar, staff_headers

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("demo_catalog")]

ADMIN = "+8801911200001"
CONTENT = "+8801911200002"
ROOT = "+8801911200003"


async def _geo(client: httpx.AsyncClient) -> dict[str, str]:
    districts = (await client.get("/api/v1/geo/districts")).json()["data"]
    dhaka = next(d for d in districts if d["code"] == "dhaka")
    ctg = next(d for d in districts if d["code"] == "chattogram")
    upazilas = (
        await client.get("/api/v1/geo/upazilas", params={"district_id": dhaka["id"]})
    ).json()
    banani = next(u for u in upazilas["data"] if u["name"] == "Banani")
    areas = (await client.get("/api/v1/geo/areas", params={"upazila_id": banani["id"]})).json()
    return {
        "district_id": dhaka["id"],
        "other_district_id": ctg["id"],
        "upazila_id": banani["id"],
        "area_id": areas["data"][0]["id"],
    }


async def test_geography_is_complete_at_district_level(client: httpx.AsyncClient) -> None:
    divisions = (await client.get("/api/v1/geo/divisions")).json()["data"]
    assert len(divisions) == 8
    districts = (await client.get("/api/v1/geo/districts")).json()["data"]
    assert len(districts) == 64
    dhaka_div = next(d for d in divisions if d["code"] == "dhaka")
    assert dhaka_div["name_bn"] == "ঢাকা"
    in_dhaka = (
        await client.get("/api/v1/geo/districts", params={"division_id": dhaka_div["id"]})
    ).json()["data"]
    assert len(in_dhaka) == 13


async def test_centre_locator(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/v1/centres", params={"lat": 23.7925, "lng": 90.4078})
    centres = res.json()["data"]
    assert centres[0]["slug"] == "gulshan" and centres[0]["distance_km"] == 0
    assert [c["distance_km"] for c in centres] == sorted(c["distance_km"] for c in centres)

    near = await client.get(
        "/api/v1/centres", params={"lat": 23.7925, "lng": 90.4078, "radius_km": 5}
    )
    assert {c["slug"] for c in near.json()["data"]} == {"gulshan", "mirpur-10"}

    xray = await client.get("/api/v1/centres", params={"service": "X_RAY"})
    assert [c["slug"] for c in xray.json()["data"]] == ["dhanmondi"]

    detail = (await client.get("/api/v1/centres/gulshan")).json()["data"]
    assert len(detail["hours"]) == 7 and detail["district"]["name"] == "Dhaka"


async def test_centre_admin_with_hours_and_geo_validation(client: httpx.AsyncClient) -> None:
    admin = await staff_headers(client, ADMIN, Role.ADMIN)
    geo = await _geo(client)
    branches = (await client.get("/api/v1/admin/branches", headers=admin)).json()["data"]
    body: dict[str, Any] = {
        "code": "DHK-BAN",
        "slug": "banani",
        "name": "Banani Centre",
        "branch_id": branches[0]["id"],
        "address": "Road 11, Banani, Dhaka",
        "district_id": geo["district_id"],
        "upazila_id": geo["upazila_id"],
        "area_id": geo["area_id"],
        "latitude": 23.794,
        "longitude": 90.405,
        "phone": "01711-000000",
        "services": ["SAMPLE_COLLECTION", "HOME_COLLECTION"],
        "hours": [
            {"weekday": d, "opens_at": "08:00", "closes_at": "20:00"} for d in (0, 1, 2, 3, 5, 6)
        ],
    }
    wrong_district = {**body, "district_id": geo["other_district_id"]}
    res = await client.post("/api/v1/admin/centres", headers=admin, json=wrong_district)
    assert res.status_code == 400
    assert res.json()["error"]["details"][0]["field"] == "upazila_id"

    overlapping = {
        **body,
        "hours": [
            {"weekday": 0, "opens_at": "08:00", "closes_at": "13:00"},
            {"weekday": 0, "opens_at": "12:00", "closes_at": "20:00"},
        ],
    }
    assert (
        await client.post("/api/v1/admin/centres", headers=admin, json=overlapping)
    ).status_code == 400

    res = await client.post("/api/v1/admin/centres", headers=admin, json=body)
    assert res.status_code == 201, res.text
    centre = res.json()["data"]
    assert centre["phone"] == "+8801711000000" and len(centre["hours"]) == 6

    # Replace the week (same keys reused) and change one field.
    res = await client.patch(
        f"/api/v1/admin/centres/{centre['id']}",
        headers={**admin, "If-Match": "1"},
        json={
            "name": "Banani Centre (DEMO)",
            "hours": [{"weekday": 0, "opens_at": "08:00", "closes_at": "22:00"}],
        },
    )
    assert res.status_code == 200, res.text
    updated = res.json()["data"]
    assert updated["hours"] == [{"weekday": 0, "opens_at": "08:00:00", "closes_at": "22:00:00"}]
    assert updated["version"] == 2

    public = (await client.get("/api/v1/centres/banani")).json()["data"]
    assert public["name"] == "Banani Centre (DEMO)"

    res = await client.delete(f"/api/v1/admin/centres/{centre['id']}", headers=admin)
    assert res.status_code == 204
    assert (await client.get("/api/v1/centres/banani")).status_code == 404


async def test_role_scope_ids_must_exist(client: httpx.AsyncClient) -> None:
    root = await staff_headers(client, ROOT, Role.SUPER_ADMIN)
    res = await client.post(
        "/api/v1/admin/users",
        headers=root,
        json={
            "full_name": "Branch Boss",
            "phone": "01811000077",
            "password": "Branch-password-1",
            "role": "BRANCH_MANAGER",
            "scope_type": "BRANCH",
            "scope_id": "01a0e389-0000-7000-8000-000000000000",
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["details"][0]["field"] == "scope_id"

    branch_id = str(await db_scalar("SELECT id FROM centre.branches WHERE code = 'DHAKA'"))
    res = await client.post(
        "/api/v1/admin/users",
        headers=root,
        json={
            "full_name": "Branch Boss",
            "phone": "01811000077",
            "password": "Branch-password-1",
            "role": "BRANCH_MANAGER",
            "scope_type": "BRANCH",
            "scope_id": branch_id,
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["roles"][0]["scope_id"] == branch_id


async def test_cms_publishing_workflow(client: httpx.AsyncClient) -> None:
    content = await staff_headers(client, CONTENT, Role.CONTENT_MANAGER)
    page = {"slug": "home-collection", "title": "Home collection", "body": "## Hello"}

    res = await client.post("/api/v1/admin/cms/pages", headers=content, json=page)
    assert res.status_code == 201, res.text
    created = res.json()["data"]
    assert created["status"] == "DRAFT"
    assert (await client.get("/api/v1/cms/pages/home-collection")).status_code == 404

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    res = await client.put(
        f"/api/v1/admin/cms/pages/{created['id']}",
        headers={**content, "If-Match": "1"},
        json={**page, "status": "PUBLISHED", "publish_at": future},
    )
    assert res.status_code == 200, res.text
    assert (await client.get("/api/v1/cms/pages/home-collection")).status_code == 404  # scheduled

    res = await client.put(
        f"/api/v1/admin/cms/pages/{created['id']}",
        headers={**content, "If-Match": "2"},
        json={**page, "status": "PUBLISHED"},
    )
    assert res.status_code == 200
    public = await client.get("/api/v1/cms/pages/home-collection")
    assert public.status_code == 200 and public.json()["data"]["body"] == "## Hello"

    sitemap = (await client.get("/api/v1/seo/sitemap")).json()["data"]
    assert ("page", "home-collection") in {(e["type"], e["slug"]) for e in sitemap}


@pytest.mark.parametrize(
    "href", ["javascript:alert(1)", "//evil.example", "http://plain.example", "data:text/html,x"]
)
async def test_banner_links_must_be_safe(client: httpx.AsyncClient, href: str) -> None:
    content = await staff_headers(client, CONTENT, Role.CONTENT_MANAGER)
    res = await client.post(
        "/api/v1/admin/cms/banners",
        headers=content,
        json={"title": "Offer", "cta_label": "Go", "cta_href": href, "status": "PUBLISHED"},
    )
    assert res.status_code == 400


async def test_banners_and_faqs_public(client: httpx.AsyncClient) -> None:
    hero = (await client.get("/api/v1/cms/banners")).json()["data"]
    assert len(hero) == 1 and hero[0]["cta_href"] == "/packages"
    faqs = (await client.get("/api/v1/cms/faqs", params={"category": "reports"})).json()["data"]
    assert len(faqs) == 2


async def test_cms_admin_requires_cms_permission(client: httpx.AsyncClient) -> None:
    admin_tech = await staff_headers(client, ADMIN, Role.LAB_TECHNICIAN)
    res = await client.get("/api/v1/admin/cms/pages", headers=admin_tech)
    assert res.status_code == 403
