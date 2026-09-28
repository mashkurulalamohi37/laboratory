"""Registry of scope resolvers used to validate RBAC scope IDs.

A role grant scoped to a BRANCH, LAB, CORPORATE or PARTNER must point at a row that exists.
The module that owns those rows registers a resolver here, so the auth module can validate
grants without importing (and depending on) every owning module.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

#: Returns True when the ID exists (and may be granted).
ScopeResolver = Callable[[AsyncSession, uuid.UUID], Awaitable[bool]]

_resolvers: dict[str, ScopeResolver] = {}


def register_scope_resolver(scope_type: str, resolver: ScopeResolver) -> None:
    _resolvers[scope_type] = resolver


async def scope_exists(session: AsyncSession, scope_type: str, scope_id: uuid.UUID) -> bool | None:
    """True/False when a resolver exists for the scope type; None when nothing owns it yet
    (for example CORPORATE and PARTNER until those modules ship)."""
    resolver = _resolvers.get(scope_type)
    if resolver is None:
        return None
    return await resolver(session, scope_id)
