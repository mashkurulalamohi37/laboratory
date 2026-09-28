"""The authenticated caller and its effective, scoped permissions."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from app.core.errors import PermissionDenied
from app.modules.auth.permissions import P, Role, ScopeType


@dataclass(frozen=True, slots=True)
class RoleGrant:
    role: str
    scope_type: str
    scope_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    session_id: uuid.UUID
    is_staff: bool
    status: str
    grants: tuple[RoleGrant, ...]
    #: permission code → set of (scope_type, scope_id) where it applies
    permissions: dict[str, frozenset[tuple[str, uuid.UUID | None]]] = field(default_factory=dict)

    @property
    def role_codes(self) -> list[str]:
        return sorted({g.role for g in self.grants})

    @property
    def is_super_admin(self) -> bool:
        return any(g.role == Role.SUPER_ADMIN for g in self.grants)

    def has(
        self, perm: P | str, scope_type: ScopeType | None = None, scope_id: uuid.UUID | None = None
    ) -> bool:
        """True if granted globally, or in the requested scope. With no scope requested,
        any grant of the permission counts (callers must then filter rows by scope)."""
        scopes = self.permissions.get(str(perm))
        if not scopes:
            return False
        if (ScopeType.GLOBAL.value, None) in scopes or scope_type is None:
            return True
        return (scope_type.value, scope_id) in scopes

    def require(
        self, perm: P | str, scope_type: ScopeType | None = None, scope_id: uuid.UUID | None = None
    ) -> None:
        if not self.has(perm, scope_type, scope_id):
            raise PermissionDenied()

    def scope_ids(self, perm: P | str, scope_type: ScopeType) -> set[uuid.UUID] | None:
        """IDs of `scope_type` where `perm` applies; `None` means unrestricted (global)."""
        scopes = self.permissions.get(str(perm), frozenset())
        if (ScopeType.GLOBAL.value, None) in scopes:
            return None
        return {sid for st, sid in scopes if st == scope_type.value and sid is not None}

    # --- cache serialisation -------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(
            {
                "user_id": str(self.user_id),
                "is_staff": self.is_staff,
                "status": self.status,
                "grants": [
                    [g.role, g.scope_type, str(g.scope_id) if g.scope_id else None]
                    for g in self.grants
                ],
                "permissions": {
                    p: [[st, str(sid) if sid else None] for st, sid in scopes]
                    for p, scopes in self.permissions.items()
                },
            }
        )

    @classmethod
    def from_json(cls, raw: str, session_id: uuid.UUID) -> Principal:
        data = json.loads(raw)

        def _uuid(v: str | None) -> uuid.UUID | None:
            return uuid.UUID(v) if v else None

        return cls(
            user_id=uuid.UUID(data["user_id"]),
            session_id=session_id,
            is_staff=data["is_staff"],
            status=data["status"],
            grants=tuple(RoleGrant(r, st, _uuid(sid)) for r, st, sid in data["grants"]),
            permissions={
                p: frozenset((st, _uuid(sid)) for st, sid in scopes)
                for p, scopes in data["permissions"].items()
            },
        )
