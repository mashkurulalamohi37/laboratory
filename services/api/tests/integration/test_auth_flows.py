"""End-to-end authentication flows against real PostgreSQL + Redis."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import REFRESH_COOKIE
from app.modules.auth.permissions import Role
from tests.integration.conftest import (
    STAFF_PASSWORD,
    bearer,
    create_staff,
    db_execute,
    db_scalar,
    last_otp,
    patient_login,
    staff_login,
)

pytestmark = pytest.mark.integration


async def test_otp_login_registers_patient(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/v1/auth/send-otp", json={"phone": "01711000001"})
    assert res.status_code == 202
    assert res.json()["data"] == {"sent": True, "expires_in": 300, "resend_after": 60}

    res = await client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "+8801711000001", "code": last_otp("+8801711000001")},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_new_user"] is True
    assert data["refresh_token"] is None  # web: cookie only
    cookie = res.headers["set-cookie"]
    assert REFRESH_COOKIE in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie

    me = (await client.get("/api/v1/me", headers=bearer(data["access_token"]))).json()["data"]
    assert me["phone"] == "+8801711000001"
    assert me["is_staff"] is False
    assert [r["role"] for r in me["roles"]] == ["PATIENT"]
    assert me["permissions"] == []

    actions = await db_scalar(
        "SELECT array_agg(action ORDER BY at) FROM audit.audit_logs WHERE entity_id = :id",
        id=me["id"],
    )
    assert actions == ["user.registered", "auth.login"]


async def test_second_login_is_not_new_user(client: httpx.AsyncClient) -> None:
    await patient_login(client)
    await client.post("/api/v1/auth/send-otp", json={"phone": "01711000001"})
    res = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": "01711000001", "code": last_otp("+8801711000001")}
    )
    assert res.json()["data"]["is_new_user"] is False


async def test_otp_attempt_limit_burns_the_code(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/send-otp", json={"phone": "01711000002"})
    code = last_otp("+8801711000002")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        res = await client.post(
            "/api/v1/auth/verify-otp", json={"phone": "01711000002", "code": wrong}
        )
        assert res.json()["error"]["code"] == "OTP_INVALID"
    res = await client.post("/api/v1/auth/verify-otp", json={"phone": "01711000002", "code": code})
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "OTP_ATTEMPTS_EXCEEDED"


async def test_otp_is_single_use(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/auth/send-otp", json={"phone": "01711000003"})
    code = last_otp("+8801711000003")
    ok = await client.post("/api/v1/auth/verify-otp", json={"phone": "01711000003", "code": code})
    again = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": "01711000003", "code": code}
    )
    assert ok.status_code == 200 and again.status_code == 401


async def test_send_otp_is_rate_limited_per_phone(client: httpx.AsyncClient) -> None:
    for _ in range(3):
        assert (
            await client.post("/api/v1/auth/send-otp", json={"phone": "01711000004"})
        ).status_code == 202
    res = await client.post("/api/v1/auth/send-otp", json={"phone": "01711000004"})
    assert res.status_code == 429
    assert int(res.headers["retry-after"]) > 0


async def test_invalid_phone_is_a_validation_error(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/v1/auth/send-otp", json={"phone": "12345"})
    assert res.status_code == 400
    assert res.json()["error"]["details"][0]["field"] == "phone"


async def test_refresh_rotates_token(client: httpx.AsyncClient) -> None:
    await patient_login(client)
    first = client.cookies.get(REFRESH_COOKIE)
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    second = client.cookies.get(REFRESH_COOKIE)
    assert first and second and first != second
    assert (
        await client.get("/api/v1/me", headers=bearer(res.json()["data"]["access_token"]))
    ).status_code == 200


async def test_refresh_reuse_after_grace_revokes_session(client: httpx.AsyncClient) -> None:
    login = await patient_login(client)
    stolen = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200
    legit = client.cookies.get(REFRESH_COOKIE)

    # Move the rotation outside the grace window, then replay the stolen token.
    await db_execute(
        "UPDATE auth.refresh_tokens SET used_at = used_at - interval '5 minutes' "
        "WHERE used_at IS NOT NULL"
    )
    client.cookies.clear()
    res = await client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: stolen or ""})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_REUSED"

    # The whole session is dead: the legitimate refresh token and access token stop working.
    res = await client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: legit or ""})
    assert res.status_code == 401
    res = await client.get("/api/v1/me", headers=login.headers)
    assert res.json()["error"]["code"] == "SESSION_REVOKED"
    # The revocation and its audit record persisted although the request failed.
    assert (
        await db_scalar("SELECT count(*) FROM auth.sessions WHERE revoke_reason = 'refresh_reuse'")
        == 1
    )
    assert (
        await db_scalar(
            "SELECT count(*) FROM audit.audit_logs WHERE action = 'auth.refresh_reuse_detected'"
        )
        == 1
    )


async def test_concurrent_refresh_within_grace_is_tolerated(client: httpx.AsyncClient) -> None:
    await patient_login(client)
    old = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200
    client.cookies.clear()
    res = await client.post("/api/v1/auth/refresh", cookies={REFRESH_COOKIE: old or ""})
    assert res.status_code == 200
    assert "set-cookie" not in res.headers  # no second rotation


async def test_logout_revokes_access_token_immediately(client: httpx.AsyncClient) -> None:
    login = await patient_login(client)
    res = await client.post("/api/v1/auth/logout", headers=login.headers)
    assert res.status_code == 204
    res = await client.get("/api/v1/me", headers=login.headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "SESSION_REVOKED"
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_sessions_list_and_revoke_other_device(client: httpx.AsyncClient) -> None:
    first = await patient_login(client)
    client.cookies.clear()
    second = await patient_login(client)
    sessions = (await client.get("/api/v1/auth/sessions", headers=second.headers)).json()["data"]
    assert len(sessions) == 2
    other = next(s for s in sessions if not s["current"])
    res = await client.delete(f"/api/v1/auth/sessions/{other['id']}", headers=second.headers)
    assert res.status_code == 204
    assert (await client.get("/api/v1/me", headers=first.headers)).status_code == 401
    assert (await client.get("/api/v1/me", headers=second.headers)).status_code == 200


async def test_staff_must_use_password_and_second_factor(client: httpx.AsyncClient) -> None:
    await create_staff("+8801811000001", Role.LAB_TECHNICIAN)

    # OTP-only login is not available to staff (and no SMS is sent).
    await client.post("/api/v1/auth/send-otp", json={"phone": "01811000001"})
    with pytest.raises(AssertionError):
        last_otp("+8801811000001")

    res = await client.post(
        "/api/v1/auth/login", json={"identifier": "01811000001", "password": STAFF_PASSWORD}
    )
    challenge = res.json()["data"]
    assert challenge["two_factor_required"] is True
    assert "access_token" not in challenge
    assert challenge["phone_hint"].endswith("001") and "1811000" not in challenge["phone_hint"]

    wrong = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"challenge_id": challenge["challenge_id"], "code": "999999"},
    )
    assert wrong.status_code == 401

    staff = await staff_login(client, "+8801811000001")
    me = (await client.get("/api/v1/me", headers=staff.headers)).json()["data"]
    assert me["is_staff"] is True
    assert "result:enter" in me["permissions"]
    assert "result:verify" not in me["permissions"]


async def test_wrong_password_is_audited_and_rate_limited(client: httpx.AsyncClient) -> None:
    await create_staff("+8801811000002", Role.RECEPTIONIST)
    for _ in range(5):
        res = await client.post(
            "/api/v1/auth/login", json={"identifier": "01811000002", "password": "nope-nope-1"}
        )
        assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"
    res = await client.post(
        "/api/v1/auth/login", json={"identifier": "01811000002", "password": STAFF_PASSWORD}
    )
    assert res.status_code == 429
    assert (
        await db_scalar("SELECT count(*) FROM audit.audit_logs WHERE action = 'auth.login_failed'")
        == 5
    )


async def test_unknown_user_login_matches_wrong_password(client: httpx.AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "whatever1"}
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_password_set_login_and_reset(client: httpx.AsyncClient) -> None:
    login = await patient_login(client, "01711000009")
    res = await client.post(
        "/api/v1/auth/password/change",
        headers=login.headers,
        json={"new_password": "Patient-pass-1"},
    )
    assert res.status_code == 204

    res = await client.post(
        "/api/v1/auth/login", json={"identifier": "01711000009", "password": "Patient-pass-1"}
    )
    assert res.status_code == 200 and "access_token" in res.json()["data"]

    await client.post("/api/v1/auth/password/forgot", json={"phone": "01711000009"})
    res = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "phone": "01711000009",
            "code": last_otp("+8801711000009"),
            "new_password": "Patient-pass-2",
        },
    )
    assert res.status_code == 204
    # Reset signs out every session.
    assert (await client.get("/api/v1/me", headers=login.headers)).status_code == 401
    res = await client.post(
        "/api/v1/auth/login", json={"identifier": "01711000009", "password": "Patient-pass-1"}
    )
    assert res.status_code == 401


async def test_weak_password_rejected(client: httpx.AsyncClient) -> None:
    login = await patient_login(client)
    res = await client.post(
        "/api/v1/auth/password/change", headers=login.headers, json={"new_password": "short"}
    )
    assert res.status_code == 400


async def test_profile_update(client: httpx.AsyncClient) -> None:
    login = await patient_login(client)
    res = await client.patch(
        "/api/v1/me",
        headers=login.headers,
        json={"full_name": "Rahima Begum", "preferred_language": "bn"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["full_name"] == "Rahima Begum"
    assert res.json()["data"]["preferred_language"] == "bn"


async def test_missing_and_garbage_tokens(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/me")).json()["error"]["code"] == "AUTH_REQUIRED"
    res = await client.get("/api/v1/me", headers=bearer("not.a.jwt"))
    assert res.json()["error"]["code"] == "TOKEN_INVALID"


async def test_health_and_readiness(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).json() == {"status": "ok"}
    res = await client.get("/ready")
    body = res.json()
    assert body["checks"]["postgres"] == "ok" and body["checks"]["redis"] == "ok"
    assert res.status_code == 200  # storage is informational only
    assert "x-request-id" in res.headers
