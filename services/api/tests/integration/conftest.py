"""Integration fixtures: a migrated, seeded PostgreSQL database and a clean Redis DB."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.db import dispose_engine, get_sessionmaker
from app.core.phone import normalize_bd_phone
from app.core.redis import close_redis, get_redis
from app.core.security import hash_password
from app.modules.auth.models import User, UserRole
from app.modules.auth.permissions import Role, ScopeType
from app.modules.auth.repository import AuthRepository
from app.modules.notification.sms import ConsoleSmsProvider, get_sms_provider
from app.scripts.seed import seed_rbac
from app.scripts.seed_catalog import seed_catalog_demo
from app.scripts.seed_geo import seed_geo

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[2]
DATA_TABLES = [
    "auth.refresh_tokens",
    "auth.sessions",
    "auth.user_roles",
    "auth.users",
    "core.outbox_events",
    # Catalogue, centres and CMS are rebuilt per test (the `demo_catalog` fixture seeds them);
    # BD geography is reference data seeded once per session.
    "catalog.price_list_items",
    "catalog.price_lists",
    "catalog.search_synonyms",
    "catalog.concern_packages",
    "catalog.concern_tests",
    "catalog.health_concerns",
    "catalog.package_tests",
    "catalog.packages",
    "catalog.reference_ranges",
    "catalog.test_parameters",
    "catalog.tests",
    "catalog.preparations",
    "catalog.sample_types",
    "catalog.categories",
    "catalog.departments",
    "centre.centre_hours",
    "centre.centres",
    "centre.holidays",
    "centre.labs",
    "centre.branches",
    "cms.banners",
    "cms.pages",
    "cms.faqs",
]
STAFF_PASSWORD = "Staff-password-2026"


def _asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _ensure_database(url: str) -> None:
    dsn = _asyncpg_dsn(url)
    base, dbname = dsn.rsplit("/", 1)
    try:
        conn = await asyncpg.connect(f"{base}/postgres", timeout=3)
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.skip(f"PostgreSQL unavailable for integration tests: {exc}")
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def _infrastructure() -> AsyncIterator[None]:
    url = os.environ["DATABASE_URL"]
    await _ensure_database(url)
    try:
        await Redis.from_url(os.environ["REDIS_URL"]).ping()
    except Exception as exc:
        pytest.skip(f"Redis unavailable for integration tests: {exc}")

    conn = await asyncpg.connect(_asyncpg_dsn(url))
    await conn.execute("DROP SCHEMA IF EXISTS audit, auth, core, geo, centre, catalog, cms CASCADE")
    await conn.close()

    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    await asyncio.to_thread(command.upgrade, cfg, "head")

    async with get_sessionmaker()() as session, session.begin():
        await seed_rbac(session, reset_mappings=True)
        await seed_geo(session)
    yield
    await dispose_engine()
    await close_redis()


@pytest.fixture(autouse=True)
async def _clean_state() -> AsyncIterator[None]:
    async with get_sessionmaker()() as session, session.begin():
        await session.execute(text(f"TRUNCATE {', '.join(DATA_TABLES)} CASCADE"))
        await session.execute(text("ALTER TABLE audit.audit_logs DISABLE TRIGGER USER"))
        await session.execute(text("TRUNCATE audit.audit_logs"))
        await session.execute(text("ALTER TABLE audit.audit_logs ENABLE TRIGGER USER"))
    await get_redis().flushdb()
    provider = get_sms_provider()
    assert isinstance(provider, ConsoleSmsProvider)
    provider.outbox.clear()
    yield


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from app.main import create_app

    transport = httpx.ASGITransport(app=create_app(), client=("203.0.113.10", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


def last_otp(phone: str) -> str:
    provider = get_sms_provider()
    assert isinstance(provider, ConsoleSmsProvider)
    message = provider.last_to(phone)
    assert message is not None, f"no SMS sent to {phone}"
    match = re.search(r"\b(\d{6})\b", message.body)
    assert match
    return match.group(1)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class LoggedIn:
    user_id: str
    phone: str
    access_token: str

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.access_token)


async def patient_login(client: httpx.AsyncClient, phone: str = "01711000001") -> LoggedIn:
    res = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert res.status_code == 202, res.text
    e164 = normalize_bd_phone(phone)
    res = await client.post(
        "/api/v1/auth/verify-otp", json={"phone": phone, "code": last_otp(e164)}
    )
    assert res.status_code == 200, res.text
    token = res.json()["data"]["access_token"]
    me = (await client.get("/api/v1/me", headers=bearer(token))).json()["data"]
    return LoggedIn(me["id"], e164, token)


async def create_staff(phone: str, role: Role, name: str = "Test Staff") -> str:
    async with get_sessionmaker()() as session, session.begin():
        user = User(
            phone=phone, full_name=name, password_hash=hash_password(STAFF_PASSWORD), is_staff=True
        )
        session.add(user)
        await session.flush()
        role_row = await AuthRepository(session).get_role_by_code(role.value)
        assert role_row is not None
        session.add(UserRole(user_id=user.id, role_id=role_row.id, scope_type=ScopeType.GLOBAL))
        return str(user.id)


async def staff_login(client: httpx.AsyncClient, phone: str) -> LoggedIn:
    res = await client.post(
        "/api/v1/auth/login", json={"identifier": phone, "password": STAFF_PASSWORD}
    )
    assert res.status_code == 200, res.text
    challenge = res.json()["data"]
    assert challenge["two_factor_required"] is True
    res = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"challenge_id": challenge["challenge_id"], "code": last_otp(phone)},
    )
    assert res.status_code == 200, res.text
    token = res.json()["data"]["access_token"]
    me = (await client.get("/api/v1/me", headers=bearer(token))).json()["data"]
    return LoggedIn(me["id"], phone, token)


async def db_scalar(sql: str, **params: object) -> object:
    async with get_sessionmaker()() as session:
        return (await session.execute(text(sql), params)).scalar()


async def db_execute(sql: str, **params: object) -> None:
    async with get_sessionmaker()() as session, session.begin():
        await session.execute(text(sql), params)


@pytest.fixture
async def demo_catalog() -> None:
    """The DEMO catalogue, centres and CMS content (fresh for each test)."""
    async with get_sessionmaker()() as session, session.begin():
        await seed_catalog_demo(session)


async def staff_headers(client: httpx.AsyncClient, phone: str, role: Role) -> dict[str, str]:
    await create_staff(phone, role, f"Test {role.value}")
    return (await staff_login(client, phone)).headers
