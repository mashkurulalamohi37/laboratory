"""RBAC enforcement and access administration against real PostgreSQL + Redis."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy.exc import DBAPIError

from app.modules.auth.permissions import Role
from tests.integration.conftest import (
    bearer,
    create_staff,
    db_execute,
    db_scalar,
    last_otp,
    patient_login,
    staff_login,
)

pytestmark = pytest.mark.integration

SUPER = "+8801911000001"
ADMIN = "+8801911000002"


async def _super_admin(client: httpx.AsyncClient) -> dict[str, str]:
    await create_staff(SUPER, Role.SUPER_ADMIN, "Root")
    return (await staff_login(client, SUPER)).headers


async def test_patient_cannot_reach_admin_endpoints(client: httpx.AsyncClient) -> None:
    patient = await patient_login(client)
    for method, url in [
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v1/admin/roles"),
        ("GET", "/api/v1/admin/audit-logs"),
    ]:
        res = await client.request(method, url, headers=patient.headers)
        assert res.status_code == 403, url
        assert res.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_super_admin_creates_staff_and_grant_takes_effect_immediately(
    client: httpx.AsyncClient,
) -> None:
    root = await _super_admin(client)
    res = await client.post(
        "/api/v1/admin/users",
        headers=root,
        json={
            "full_name": "Tania Tech",
            "phone": "01811000010",
            "password": "Tech-password-1",
            "role": "LAB_TECHNICIAN",
        },
    )
    assert res.status_code == 201, res.text
    tech_id = res.json()["data"]["id"]
    assert res.json()["data"]["roles"][0]["role"] == "LAB_TECHNICIAN"

    # Log the technician in directly (different password from STAFF_PASSWORD).
    res = await client.post(
        "/api/v1/auth/login", json={"identifier": "01811000010", "password": "Tech-password-1"}
    )
    challenge = res.json()["data"]["challenge_id"]
    res = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"challenge_id": challenge, "code": last_otp("+8801811000010")},
    )
    tech = bearer(res.json()["data"]["access_token"])
    assert (await client.get("/api/v1/admin/users", headers=tech)).status_code == 403

    res = await client.post(
        f"/api/v1/admin/users/{tech_id}/roles", headers=root, json={"role": "BRANCH_MANAGER"}
    )
    assert res.status_code == 201
    # BRANCH_MANAGER lacks user:manage → still denied; grant ADMIN (user:manage) instead.
    assert (await client.get("/api/v1/admin/users", headers=tech)).status_code == 403
    res = await client.post(
        f"/api/v1/admin/users/{tech_id}/roles", headers=root, json={"role": "ADMIN"}
    )
    assert res.status_code == 201
    # Cached principal was invalidated on commit: same token, new permission.
    assert (await client.get("/api/v1/admin/users", headers=tech)).status_code == 200

    audit = await db_scalar(
        "SELECT count(*) FROM audit.audit_logs WHERE action = 'user.role_assigned' "
        "AND entity_id = :id",
        id=tech_id,
    )
    assert audit == 2


async def test_duplicate_staff_phone_conflicts(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    body = {
        "full_name": "A Person",
        "phone": "01811000011",
        "password": "Password-123",
        "role": "RECEPTIONIST",
    }
    assert (await client.post("/api/v1/admin/users", headers=root, json=body)).status_code == 201
    res = await client.post("/api/v1/admin/users", headers=root, json=body)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "USER_ALREADY_EXISTS"


async def test_admin_cannot_grant_privileged_roles(client: httpx.AsyncClient) -> None:
    await create_staff(ADMIN, Role.ADMIN, "Plain Admin")
    admin = (await staff_login(client, ADMIN)).headers
    patient = await patient_login(client)
    res = await client.post(
        f"/api/v1/admin/users/{patient.user_id}/roles", headers=admin, json={"role": "SUPER_ADMIN"}
    )
    assert res.status_code == 403
    # ADMIN lacks role:manage entirely by default.
    res = await client.post(
        f"/api/v1/admin/users/{patient.user_id}/roles", headers=admin, json={"role": "RECEPTIONIST"}
    )
    assert res.status_code == 403


async def test_scope_validation(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    patient = await patient_login(client)
    res = await client.post(
        f"/api/v1/admin/users/{patient.user_id}/roles",
        headers=root,
        json={"role": "RECEPTIONIST", "scope_type": "BRANCH"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["details"][0]["field"] == "scope_id"


async def test_last_super_admin_and_self_protection(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    me = (await client.get("/api/v1/me", headers=root)).json()["data"]
    res = await client.patch(
        f"/api/v1/admin/users/{me['id']}/status",
        headers=root,
        json={"status": "DISABLED", "reason": "testing"},
    )
    assert res.json()["error"]["code"] == "SELF_MODIFICATION_FORBIDDEN"
    detail = (await client.get(f"/api/v1/admin/users/{me['id']}", headers=root)).json()["data"]
    grant_id = detail["roles"][0]["id"]
    res = await client.delete(f"/api/v1/admin/users/{me['id']}/roles/{grant_id}", headers=root)
    assert res.status_code == 422


async def test_suspending_user_ends_their_sessions(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    patient = await patient_login(client)
    res = await client.patch(
        f"/api/v1/admin/users/{patient.user_id}/status",
        headers=root,
        json={"status": "SUSPENDED", "reason": "fraud investigation"},
    )
    assert res.status_code == 200 and res.json()["data"]["status"] == "SUSPENDED"
    res = await client.get("/api/v1/me", headers=patient.headers)
    assert res.status_code == 401
    # A suspended user cannot sign back in by OTP either (no code is delivered).
    await client.post("/api/v1/auth/send-otp", json={"phone": patient.phone})
    before = await db_scalar(
        "SELECT count(*) FROM auth.sessions WHERE user_id = :id", id=patient.user_id
    )
    assert before == 1


async def test_role_permission_editing(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    res = await client.put(
        "/api/v1/admin/roles/SUPER_ADMIN/permissions", headers=root, json={"permissions": []}
    )
    assert res.json()["error"]["code"] == "ROLE_IMMUTABLE"
    res = await client.put(
        "/api/v1/admin/roles/DOCTOR/permissions",
        headers=root,
        json={"permissions": ["report:view", "made:up"]},
    )
    assert res.status_code == 400
    res = await client.put(
        "/api/v1/admin/roles/DOCTOR/permissions",
        headers=root,
        json={"permissions": ["report:view"]},
    )
    assert res.status_code == 200
    assert res.json()["data"]["permissions"] == ["report:view"]
    roles = (await client.get("/api/v1/admin/roles", headers=root)).json()["data"]
    assert next(r for r in roles if r["code"] == "DOCTOR")["permissions"] == ["report:view"]


async def test_audit_log_is_queryable_and_immutable(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    res = await client.get(
        "/api/v1/admin/audit-logs", headers=root, params={"action": "auth.login"}
    )
    assert res.status_code == 200
    logs = res.json()["data"]
    assert logs and logs[0]["ip"] == "203.0.113.10" and logs[0]["request_id"]
    assert res.json()["meta"]["total"] >= 1

    with pytest.raises(DBAPIError, match="append-only"):
        await db_execute("UPDATE audit.audit_logs SET action = 'tampered'")
    with pytest.raises(DBAPIError, match="append-only"):
        await db_execute("DELETE FROM audit.audit_logs")


async def test_users_list_pagination_and_search(client: httpx.AsyncClient) -> None:
    root = await _super_admin(client)
    for i in range(3):
        await patient_login(client, f"0171100010{i}")
    res = await client.get(
        "/api/v1/admin/users", headers=root, params={"is_staff": "false", "page_size": 2}
    )
    body = res.json()
    assert len(body["data"]) == 2 and body["meta"]["total"] == 3
    res = await client.get("/api/v1/admin/users", headers=root, params={"q": "17110001"})
    assert res.json()["meta"]["total"] == 3
