"""Data access for the auth schema."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.sql import escape_like
from app.modules.auth.models import (
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    Session,
    User,
    UserRole,
)


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    # users -------------------------------------------------------------------
    async def get_user(self, user_id: uuid.UUID, *, for_update: bool = False) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def get_user_by_phone(self, phone: str) -> User | None:
        return (await self.s.execute(select(User).where(User.phone == phone))).scalar_one_or_none()

    async def get_user_by_identifier(self, identifier: str) -> User | None:
        return (
            await self.s.execute(
                select(User).where(or_(User.phone == identifier, User.email == identifier))
            )
        ).scalar_one_or_none()

    async def list_users(
        self, *, q: str | None, is_staff: bool | None, status: str | None, page: int, page_size: int
    ) -> tuple[Sequence[User], int]:
        filters = []
        if q:
            term = escape_like(q.strip())
            like = f"%{term.lower()}%"
            filters.append(
                or_(
                    func.lower(User.full_name).like(like, escape="\\"),
                    User.email.like(like, escape="\\"),
                    User.phone.like(f"%{term}%", escape="\\"),
                )
            )
        if is_staff is not None:
            filters.append(User.is_staff.is_(is_staff))
        if status:
            filters.append(User.status == status)
        total = (
            await self.s.execute(select(func.count()).select_from(User).where(*filters))
        ).scalar_one()
        rows = (
            (
                await self.s.execute(
                    select(User)
                    .where(*filters)
                    .options(selectinload(User.roles))
                    .order_by(User.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return rows, int(total)

    async def get_user_with_roles(self, user_id: uuid.UUID) -> User | None:
        return (
            await self.s.execute(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.roles).joinedload(UserRole.role))
                # Refresh objects already in the session (e.g. a just-added UserRole whose
                # `role` was never loaded) instead of reusing stale identity-map state.
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    # roles & permissions -----------------------------------------------------
    async def get_role_by_code(self, code: str) -> Role | None:
        return (await self.s.execute(select(Role).where(Role.code == code))).scalar_one_or_none()

    async def list_roles(self) -> Sequence[Role]:
        return (
            (
                await self.s.execute(
                    select(Role).options(selectinload(Role.permissions)).order_by(Role.code)
                )
            )
            .scalars()
            .all()
        )

    async def list_permissions(self) -> Sequence[Permission]:
        return (await self.s.execute(select(Permission).order_by(Permission.code))).scalars().all()

    async def get_permissions_by_codes(self, codes: set[str]) -> Sequence[Permission]:
        return (
            (await self.s.execute(select(Permission).where(Permission.code.in_(codes))))
            .scalars()
            .all()
        )

    async def effective_grants(
        self, user_id: uuid.UUID
    ) -> list[tuple[str, str, uuid.UUID | None, str | None]]:
        """(role_code, scope_type, scope_id, permission_code|None) rows for a user."""
        stmt = (
            select(Role.code, UserRole.scope_type, UserRole.scope_id, Permission.code)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .outerjoin(RolePermission, RolePermission.role_id == Role.id)
            .outerjoin(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRole.user_id == user_id)
        )
        return [tuple(r) for r in (await self.s.execute(stmt)).all()]  # type: ignore[misc]

    async def replace_role_permissions(
        self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]
    ) -> None:
        await self.s.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        if permission_ids:
            await self.s.execute(
                insert(RolePermission),
                [{"role_id": role_id, "permission_id": pid} for pid in permission_ids],
            )

    async def find_user_role(
        self, user_id: uuid.UUID, role_id: uuid.UUID, scope_type: str, scope_id: uuid.UUID | None
    ) -> UserRole | None:
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.scope_type == scope_type,
            UserRole.scope_id.is_(None) if scope_id is None else UserRole.scope_id == scope_id,
        )
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def get_user_role(self, user_role_id: uuid.UUID) -> UserRole | None:
        return (
            await self.s.execute(select(UserRole).where(UserRole.id == user_role_id))
        ).scalar_one_or_none()

    async def count_role_holders(self, role_code: str) -> int:
        stmt = (
            select(func.count(func.distinct(UserRole.user_id)))
            .join(Role, Role.id == UserRole.role_id)
            .join(User, User.id == UserRole.user_id)
            .where(Role.code == role_code, User.status == "ACTIVE")
        )
        return int((await self.s.execute(stmt)).scalar_one())

    # sessions & tokens -------------------------------------------------------
    async def get_session(self, session_id: uuid.UUID) -> Session | None:
        return (
            await self.s.execute(select(Session).where(Session.id == session_id))
        ).scalar_one_or_none()

    async def list_active_sessions(self, user_id: uuid.UUID) -> Sequence[Session]:
        return (
            (
                await self.s.execute(
                    select(Session)
                    .where(
                        Session.user_id == user_id,
                        Session.revoked_at.is_(None),
                        Session.expires_at > func.now(),
                    )
                    .order_by(Session.last_seen_at.desc())
                )
            )
            .scalars()
            .all()
        )

    async def get_refresh_token_for_update(self, token_hash: str) -> RefreshToken | None:
        return (
            await self.s.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
            )
        ).scalar_one_or_none()

    async def revoke_sessions(
        self,
        user_id: uuid.UUID,
        *,
        reason: str,
        now: datetime,
        only: uuid.UUID | None = None,
        except_session: uuid.UUID | None = None,
    ) -> list[uuid.UUID]:
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now, revoke_reason=reason)
            .returning(Session.id)
        )
        if only is not None:
            stmt = stmt.where(Session.id == only)
        if except_session is not None:
            stmt = stmt.where(Session.id != except_session)
        return list((await self.s.execute(stmt)).scalars().all())
