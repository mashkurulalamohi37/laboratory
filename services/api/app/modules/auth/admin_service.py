"""Access administration: staff users, account status, role grants and role permissions.

Guard rails enforced here (not in the UI):
- only SUPER_ADMIN can grant/revoke privileged roles or act on SUPER_ADMIN accounts;
- nobody can change their own status or remove their own SUPER_ADMIN grant;
- the last active SUPER_ADMIN cannot be disabled or demoted;
- SUPER_ADMIN's permission set is immutable.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import on_commit
from app.core.errors import (
    BusinessRuleViolation,
    Conflict,
    ErrorDetail,
    NotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.core.scopes import scope_exists
from app.core.security import hash_password
from app.modules.audit import service as audit
from app.modules.auth.dependencies import (
    invalidate_all_principals,
    invalidate_principal,
    mark_sessions_revoked,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.permissions import PRIVILEGED_ROLES, STAFF_ROLES, P, Role, ScopeType
from app.modules.auth.principal import Principal
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    AssignRoleRequest,
    CreateStaffUserRequest,
    PermissionOut,
    RoleOut,
    UserOut,
    UserRoleOut,
)


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        phone=user.phone,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        is_staff=user.is_staff,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=[
            UserRoleOut(
                id=r.id,
                role=r.role.code,
                scope_type=r.scope_type,
                scope_id=r.scope_id,
                created_at=r.created_at,
            )
            for r in user.roles
        ],
    )


async def _validate_scope(
    session: AsyncSession, scope_type: ScopeType, scope_id: uuid.UUID | None
) -> None:
    if (scope_type is ScopeType.GLOBAL) != (scope_id is None):
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field="scope_id",
                    issue="must be empty for GLOBAL scope and set for any other scope",
                )
            ]
        )
    if scope_id is not None and await scope_exists(session, scope_type.value, scope_id) is False:
        raise ValidationFailed(
            details=[
                ErrorDetail(field="scope_id", issue=f"no {scope_type.value.lower()} with this id")
            ]
        )


class AccessAdminService:
    def __init__(self, session: AsyncSession, actor: Principal) -> None:
        self.s = session
        self.repo = AuthRepository(session)
        self.actor = actor

    def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: object,
        *,
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
    ) -> None:
        audit.record(
            self.s,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_user_id=self.actor.user_id,
            actor_roles=self.actor.role_codes,
            before=before,
            after=after,
        )

    def _require_can_grant(self, role_code: str) -> None:
        if role_code in PRIVILEGED_ROLES and not self.actor.is_super_admin:
            raise PermissionDenied("Only a super admin can manage this role.")

    async def _load_user(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_user_with_roles(user_id)
        if user is None:
            raise NotFound()
        return user

    def _guard_target(self, user: User) -> None:
        if (
            any(r.role.code == Role.SUPER_ADMIN for r in user.roles)
            and not self.actor.is_super_admin
        ):
            raise PermissionDenied("Only a super admin can manage a super admin account.")

    # ------------------------------------------------------------------ users
    async def list_users(
        self, *, q: str | None, is_staff: bool | None, status: str | None, page: int, page_size: int
    ) -> tuple[list[UserOut], int]:
        rows, total = await self.repo.list_users(
            q=q, is_staff=is_staff, status=status, page=page, page_size=page_size
        )
        return [_user_out(u) for u in rows], total

    async def get_user(self, user_id: uuid.UUID) -> UserOut:
        return _user_out(await self._load_user(user_id))

    async def create_staff_user(self, req: CreateStaffUserRequest) -> UserOut:
        if req.role not in STAFF_ROLES:
            raise ValidationFailed(
                details=[ErrorDetail(field="role", issue="must be a staff role")]
            )
        self._require_can_grant(req.role)
        await _validate_scope(self.s, req.scope_type, req.scope_id)
        role = await self.repo.get_role_by_code(req.role)
        if role is None:
            raise ValidationFailed(details=[ErrorDetail(field="role", issue="unknown role")])

        if await self.repo.get_user_by_phone(req.phone) or (
            req.email and await self.repo.get_user_by_identifier(req.email.lower())
        ):
            raise Conflict(
                "A user with this phone or email already exists.", code="USER_ALREADY_EXISTS"
            )
        user = User(
            full_name=req.full_name.strip(),
            phone=req.phone,
            email=req.email.lower() if req.email else None,
            password_hash=hash_password(req.password),
            is_staff=True,
        )
        self.s.add(user)
        try:
            await self.s.flush()
        except IntegrityError as exc:
            raise Conflict(
                "A user with this phone or email already exists.", code="USER_ALREADY_EXISTS"
            ) from exc
        self.s.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                scope_type=req.scope_type,
                scope_id=req.scope_id,
                granted_by=self.actor.user_id,
            )
        )
        await self.s.flush()
        self._audit(
            "user.staff_created",
            "user",
            user.id,
            after={
                "full_name": user.full_name,
                "role": req.role,
                "scope_type": req.scope_type.value,
                "scope_id": req.scope_id,
            },
        )
        return _user_out(await self._load_user(user.id))

    async def update_status(self, user_id: uuid.UUID, status: str, reason: str) -> UserOut:
        if user_id == self.actor.user_id:
            raise BusinessRuleViolation(
                "You cannot change your own account status.", code="SELF_MODIFICATION_FORBIDDEN"
            )
        user = await self._load_user(user_id)
        self._guard_target(user)
        if status == user.status:
            return _user_out(user)
        if (
            status != "ACTIVE"
            and any(r.role.code == Role.SUPER_ADMIN for r in user.roles)
            and await self.repo.count_role_holders(Role.SUPER_ADMIN) <= 1
        ):
            raise BusinessRuleViolation(
                "The last super admin cannot be deactivated.", code="LAST_SUPER_ADMIN"
            )
        before = user.status
        user.status = status
        user.version += 1
        revoked: list[uuid.UUID] = []
        if status != "ACTIVE":
            revoked = await self.repo.revoke_sessions(
                user.id, reason=f"status_{status.lower()}", now=datetime.now(UTC)
            )
        self._audit(
            "user.status_changed",
            "user",
            user.id,
            before={"status": before},
            after={"status": status, "reason": reason},
        )
        on_commit(self.s, lambda: invalidate_principal(user_id))
        on_commit(self.s, lambda: mark_sessions_revoked(revoked))
        return _user_out(user)

    # ------------------------------------------------------------------ role grants
    async def assign_role(self, user_id: uuid.UUID, req: AssignRoleRequest) -> UserOut:
        self._require_can_grant(req.role)
        await _validate_scope(self.s, req.scope_type, req.scope_id)
        user = await self._load_user(user_id)
        self._guard_target(user)
        role = await self.repo.get_role_by_code(req.role)
        if role is None:
            raise ValidationFailed(details=[ErrorDetail(field="role", issue="unknown role")])
        if await self.repo.find_user_role(user.id, role.id, req.scope_type, req.scope_id):
            raise Conflict(
                "This role is already assigned in that scope.", code="ROLE_ALREADY_ASSIGNED"
            )
        if req.role in STAFF_ROLES:
            if not user.phone:
                raise BusinessRuleViolation(
                    "Staff accounts need a phone number for sign-in verification.",
                    code="STAFF_PHONE_REQUIRED",
                )
            user.is_staff = True
        self.s.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                scope_type=req.scope_type,
                scope_id=req.scope_id,
                granted_by=self.actor.user_id,
            )
        )
        user.version += 1
        await self.s.flush()
        self._audit(
            "user.role_assigned",
            "user",
            user.id,
            after={"role": req.role, "scope_type": req.scope_type.value, "scope_id": req.scope_id},
        )
        on_commit(self.s, lambda: invalidate_principal(user_id))
        return _user_out(await self._load_user(user_id))

    async def revoke_role(self, user_id: uuid.UUID, user_role_id: uuid.UUID) -> UserOut:
        user = await self._load_user(user_id)
        grant = next((r for r in user.roles if r.id == user_role_id), None)
        if grant is None:
            raise NotFound()
        self._require_can_grant(grant.role.code)
        self._guard_target(user)
        if grant.role.code == Role.SUPER_ADMIN:
            if user_id == self.actor.user_id:
                raise BusinessRuleViolation(
                    "You cannot remove your own super admin role.",
                    code="SELF_MODIFICATION_FORBIDDEN",
                )
            if await self.repo.count_role_holders(Role.SUPER_ADMIN) <= 1:
                raise BusinessRuleViolation(
                    "The last super admin cannot be removed.", code="LAST_SUPER_ADMIN"
                )
        removed = {
            "role": grant.role.code,
            "scope_type": grant.scope_type,
            "scope_id": grant.scope_id,
        }
        await self.s.delete(grant)
        user.is_staff = any(r.role.code in STAFF_ROLES for r in user.roles if r.id != user_role_id)
        user.version += 1
        await self.s.flush()
        self._audit("user.role_revoked", "user", user.id, before=removed)
        on_commit(self.s, lambda: invalidate_principal(user_id))
        return _user_out(await self._load_user(user_id))

    # ------------------------------------------------------------------ roles
    async def list_roles(self) -> list[RoleOut]:
        return [
            RoleOut(
                code=r.code,
                name=r.name,
                description=r.description,
                is_system=r.is_system,
                permissions=sorted(p.code for p in r.permissions)
                if r.code != Role.SUPER_ADMIN
                else sorted(p.value for p in P),
            )
            for r in await self.repo.list_roles()
        ]

    async def list_permissions(self) -> list[PermissionOut]:
        return [
            PermissionOut(code=p.code, description=p.description)
            for p in await self.repo.list_permissions()
        ]

    async def update_role_permissions(self, role_code: str, codes: list[str]) -> RoleOut:
        if role_code == Role.SUPER_ADMIN:
            raise BusinessRuleViolation(
                "Super admin permissions cannot be changed.", code="ROLE_IMMUTABLE"
            )
        role = next((r for r in await self.repo.list_roles() if r.code == role_code), None)
        if role is None:
            raise NotFound()
        wanted = set(codes)
        perms = await self.repo.get_permissions_by_codes(wanted)
        unknown = wanted - {p.code for p in perms}
        if unknown:
            raise ValidationFailed(
                details=[
                    ErrorDetail(field="permissions", issue=f"unknown: {', '.join(sorted(unknown))}")
                ]
            )
        before = sorted(p.code for p in role.permissions)
        await self.repo.replace_role_permissions(role.id, [p.id for p in perms])
        after = sorted(wanted)
        self._audit(
            "role.permissions_updated",
            "role",
            role.code,
            before={"permissions": before},
            after={"permissions": after},
        )
        on_commit(self.s, invalidate_all_principals)
        return RoleOut(
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=after,
        )
