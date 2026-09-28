"""Idempotent seed: permissions, roles, default role→permission mappings, bootstrap super
admin, and (development only) clearly labelled demo staff accounts.

    python -m app.scripts.seed                       # permissions + roles + super admin,
                                                     # BD geography, default price list
    python -m app.scripts.seed --demo                # + DEMO staff, catalogue, centres and
                                                     #   CMS content (development only)
    python -m app.scripts.seed --reset-role-permissions   # re-apply default mappings

Existing role→permission mappings are left untouched unless --reset-role-permissions is
given, so runtime edits made by a super admin survive re-seeding.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models_registry  # noqa: F401
from app.core.config import get_settings
from app.core.db import dispose_engine, get_sessionmaker
from app.core.phone import normalize_bd_phone
from app.core.security import hash_password
from app.modules.auth.models import Permission, Role, RolePermission, User, UserRole
from app.modules.auth.permissions import (
    PERMISSION_DESCRIPTIONS,
    ROLE_DEFAULTS,
    ROLE_NAMES,
    P,
    ScopeType,
)
from app.modules.auth.permissions import Role as RoleCode
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import validate_password_strength
from app.scripts.seed_catalog import seed_catalog_base, seed_catalog_demo
from app.scripts.seed_geo import seed_geo


class SeedSettings(BaseSettings):
    """Seed inputs, read from the environment and the same .env files as the app."""

    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    seed_superadmin_phone: str | None = None
    seed_superadmin_password: str | None = None
    seed_superadmin_name: str = "Super Admin"
    seed_superadmin_email: str | None = None
    demo_staff_password: str = ""


@lru_cache
def seed_settings() -> SeedSettings:
    return SeedSettings()


#: (role, phone, name) — phones are in an unallocated demo range pattern; names say DEMO.
DEMO_STAFF: list[tuple[RoleCode, str, str]] = [
    (RoleCode.ADMIN, "01900000001", "DEMO Admin"),
    (RoleCode.LAB_MANAGER, "01900000002", "DEMO Lab Manager"),
    (RoleCode.PATHOLOGIST, "01900000003", "DEMO Pathologist"),
    (RoleCode.LAB_TECHNICIAN, "01900000004", "DEMO Lab Technician"),
    (RoleCode.PHLEBOTOMIST, "01900000005", "DEMO Collector"),
    (RoleCode.RECEPTIONIST, "01900000006", "DEMO Receptionist"),
    (RoleCode.ACCOUNTANT, "01900000007", "DEMO Accountant"),
    (RoleCode.CUSTOMER_SUPPORT, "01900000008", "DEMO Support Agent"),
    (RoleCode.CONTENT_MANAGER, "01900000009", "DEMO Content Manager"),
    (RoleCode.INVENTORY_MANAGER, "01900000010", "DEMO Inventory Manager"),
]


def _out(msg: str) -> None:
    sys.stdout.write(msg + "\n")


async def seed_rbac(session: AsyncSession, *, reset_mappings: bool) -> None:
    existing_perms = {p.code: p for p in (await session.execute(select(Permission))).scalars()}
    introduced: set[str] = set()
    for perm in P:
        row = existing_perms.get(perm.value)
        if row is None:
            row = Permission(code=perm.value, description=PERMISSION_DESCRIPTIONS[perm])
            session.add(row)
            existing_perms[perm.value] = row
            introduced.add(perm.value)
        else:
            row.description = PERMISSION_DESCRIPTIONS[perm]
    await session.flush()

    repo = AuthRepository(session)
    for code in RoleCode:
        role = await repo.get_role_by_code(code.value)
        created = role is None
        if role is None:
            role = Role(code=code.value, name=ROLE_NAMES[code], is_system=True)
            session.add(role)
            await session.flush()
        if created or reset_mappings:
            await repo.replace_role_permissions(
                role.id, [existing_perms[p.value].id for p in ROLE_DEFAULTS[code]]
            )
            _out(
                f"  role {code.value}: {len(ROLE_DEFAULTS[code])} permissions"
                f"{' (reset)' if not created else ''}"
            )
        elif introduced:
            # A release added permissions: grant them where the defaults say so, leaving
            # every other (possibly edited) mapping of existing roles untouched.
            new = [p for p in ROLE_DEFAULTS[code] if p.value in introduced]
            if new:
                await session.execute(
                    insert(RolePermission),
                    [
                        {"role_id": role.id, "permission_id": existing_perms[p.value].id}
                        for p in new
                    ],
                )
                _out(f"  role {code.value}: +{', '.join(p.value for p in new)}")
    _out(f"[ok] {len(P)} permissions, {len(RoleCode)} roles")


async def _grant(session: AsyncSession, user: User, role_code: RoleCode) -> None:
    repo = AuthRepository(session)
    role = await repo.get_role_by_code(role_code.value)
    assert role is not None
    if not await repo.find_user_role(user.id, role.id, ScopeType.GLOBAL, None):
        session.add(UserRole(user_id=user.id, role_id=role.id, scope_type=ScopeType.GLOBAL))


async def seed_super_admin(session: AsyncSession) -> None:
    repo = AuthRepository(session)
    if await repo.count_role_holders(RoleCode.SUPER_ADMIN) > 0:
        _out("[ok] super admin already exists")
        return
    phone = seed_settings().seed_superadmin_phone
    password = seed_settings().seed_superadmin_password
    if not phone or not password:
        _out("[warn] no super admin: set SEED_SUPERADMIN_PHONE and SEED_SUPERADMIN_PASSWORD")
        return
    validate_password_strength(password)
    phone = normalize_bd_phone(phone)
    user = await repo.get_user_by_phone(phone)
    if user is None:
        user = User(
            phone=phone,
            full_name=seed_settings().seed_superadmin_name,
            email=(seed_settings().seed_superadmin_email or None),
            password_hash=hash_password(password),
            is_staff=True,
        )
        session.add(user)
        await session.flush()
    user.is_staff = True
    await _grant(session, user, RoleCode.SUPER_ADMIN)
    _out(f"[ok] super admin {phone[:6]}*****{phone[-3:]}")


async def seed_demo_staff(session: AsyncSession) -> None:
    if get_settings().environment not in ("development", "test"):
        raise SystemExit("--demo is only allowed in development/test")
    password = seed_settings().demo_staff_password
    validate_password_strength(password)
    repo = AuthRepository(session)
    for role_code, raw_phone, name in DEMO_STAFF:
        phone = normalize_bd_phone(raw_phone)
        user = await repo.get_user_by_phone(phone)
        if user is None:
            user = User(
                phone=phone, full_name=name, password_hash=hash_password(password), is_staff=True
            )
            session.add(user)
            await session.flush()
        await _grant(session, user, role_code)
    _out(f"[ok] {len(DEMO_STAFF)} DEMO staff accounts (password from DEMO_STAFF_PASSWORD)")


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--reset-role-permissions", action="store_true")
    args = parser.parse_args(argv)
    try:
        async with get_sessionmaker()() as session, session.begin():
            await seed_rbac(session, reset_mappings=args.reset_role_permissions)
            await seed_super_admin(session)
            divisions, districts, upazilas, areas = await seed_geo(session)
            _out(
                f"[ok] geography: {divisions} divisions, {districts} districts, "
                f"{upazilas} upazilas/thanas, {areas} areas"
            )
            await seed_catalog_base(session)
            if args.demo:
                await seed_demo_staff(session)
                counts = await seed_catalog_demo(session)
                _out("[ok] DEMO catalogue: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
