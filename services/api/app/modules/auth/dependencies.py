"""FastAPI dependencies for authentication and authorisation.

This is the module's public entry point for other modules:

    principal: Principal = Depends(require(P.BOOKING_VIEW))

Frontend permission checks are cosmetic; these dependencies are the enforcement point.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import AuthRequired, PermissionDenied
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.modules.auth.permissions import P, Role
from app.modules.auth.principal import Principal, RoleGrant
from app.modules.auth.repository import AuthRepository

_bearer = HTTPBearer(auto_error=False, description="JWT access token")

PRINCIPAL_CACHE_TTL = 60


class AccountDisabled(AuthRequired):
    code = "ACCOUNT_DISABLED"
    message = "This account is not active."


class SessionRevoked(AuthRequired):
    code = "SESSION_REVOKED"
    message = "This session has ended. Please sign in again."


def _principal_key(user_id: uuid.UUID) -> str:
    return f"principal:{user_id}"


def _revoked_key(session_id: uuid.UUID) -> str:
    return f"revoked-sid:{session_id}"


async def invalidate_principal(user_id: uuid.UUID) -> None:
    """Call after any change to a user's roles, role permissions or status."""
    await get_redis().delete(_principal_key(user_id))


async def invalidate_all_principals() -> None:
    redis = get_redis()
    async for key in redis.scan_iter(match="principal:*", count=500):
        await redis.delete(key)


async def mark_sessions_revoked(session_ids: list[uuid.UUID]) -> None:
    """Access tokens are short-lived JWTs; this denylist closes the gap until they expire."""
    if not session_ids:
        return
    ttl = get_settings().access_token_ttl_seconds + 60
    async with get_redis().pipeline(transaction=False) as pipe:
        for sid in session_ids:
            pipe.set(_revoked_key(sid), "1", ex=ttl)
        await pipe.execute()


async def build_principal(
    repo: AuthRepository, user_id: uuid.UUID, session_id: uuid.UUID
) -> Principal | None:
    user = await repo.get_user(user_id)
    if user is None:
        return None
    grants: set[RoleGrant] = set()
    perms: dict[str, set[tuple[str, uuid.UUID | None]]] = {}
    for role_code, scope_type, scope_id, perm_code in await repo.effective_grants(user_id):
        grants.add(RoleGrant(role_code, scope_type, scope_id))
        codes = [p.value for p in P] if role_code == Role.SUPER_ADMIN else [perm_code]
        for code in codes:
            if code:
                perms.setdefault(code, set()).add((scope_type, scope_id))
    return Principal(
        user_id=user.id,
        session_id=session_id,
        is_staff=user.is_staff,
        status=user.status,
        grants=tuple(sorted(grants, key=lambda g: (g.role, g.scope_type, str(g.scope_id)))),
        permissions={k: frozenset(v) for k, v in perms.items()},
    )


async def _load_principal(
    session: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> Principal | None:
    redis = get_redis()
    cached = await redis.get(_principal_key(user_id))
    if cached:
        return Principal.from_json(cached, session_id)
    principal = await build_principal(AuthRepository(session), user_id, session_id)
    if principal is not None:
        await redis.set(_principal_key(user_id), principal.to_json(), ex=PRINCIPAL_CACHE_TTL)
    return principal


async def get_optional_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Principal | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    claims = decode_access_token(credentials.credentials)
    if await get_redis().exists(_revoked_key(claims.session_id)):
        raise SessionRevoked()
    principal = await _load_principal(session, claims.user_id, claims.session_id)
    if principal is None:
        raise AuthRequired()
    if principal.status != "ACTIVE":
        raise AccountDisabled()
    request.state.user_id = str(principal.user_id)
    return principal


async def get_principal(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
) -> Principal:
    if principal is None:
        raise AuthRequired()
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]


def require(*perms: P, any_of: bool = False) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Route guard: all listed permissions (or any, with `any_of=True`) in some scope.

    Scope-specific checks (e.g. a given branch) belong in the service via
    `principal.require(perm, scope_type, scope_id)`.
    """

    async def dependency(principal: CurrentPrincipal) -> Principal:
        check = any if any_of else all
        if not check(principal.has(p) for p in perms):
            raise PermissionDenied()
        return principal

    separator = "_or_" if any_of else "_and_"
    dependency.__name__ = "require_" + separator.join(p.name.lower() for p in perms)
    return dependency


def require_staff() -> Callable[..., Coroutine[Any, Any, Principal]]:
    async def dependency(principal: CurrentPrincipal) -> Principal:
        if not principal.is_staff:
            raise PermissionDenied()
        return principal

    return dependency
