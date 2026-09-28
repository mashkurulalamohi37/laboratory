"""Console endpoints for user, role and permission administration."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import error_responses
from app.core.responses import Envelope, ok
from app.modules.auth.admin_service import AccessAdminService
from app.modules.auth.dependencies import require
from app.modules.auth.permissions import P
from app.modules.auth.principal import Principal
from app.modules.auth.schemas import (
    AssignRoleRequest,
    CreateStaffUserRequest,
    PermissionOut,
    RoleOut,
    UpdateRolePermissionsRequest,
    UpdateUserStatusRequest,
    UserOut,
)

router = APIRouter(prefix="/admin", tags=["admin: access"])

Db = Annotated[AsyncSession, Depends(get_session)]
UserManager = Annotated[Principal, Depends(require(P.USER_MANAGE))]
RoleManager = Annotated[Principal, Depends(require(P.ROLE_MANAGE))]
RoleViewer = Annotated[Principal, Depends(require(P.USER_MANAGE, P.ROLE_MANAGE, any_of=True))]

_ERR = error_responses(400, 401, 403, 404, 409, 422)


@router.get("/users", summary="List users", description="Requires `user:manage`.", responses=_ERR)
async def list_users(
    actor: UserManager,
    db: Db,
    q: Annotated[str | None, Query(max_length=100, description="Name, phone or email")] = None,
    is_staff: bool | None = None,
    status_: Annotated[
        Literal["ACTIVE", "SUSPENDED", "DISABLED"] | None, Query(alias="status")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[list[UserOut]]:
    items, total = await AccessAdminService(db, actor).list_users(
        q=q, is_staff=is_staff, status=status_, page=page, page_size=page_size
    )
    return ok(items, page=page, page_size=page_size, total=total)


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff user",
    description="Requires `user:manage`. Privileged roles require SUPER_ADMIN.",
    responses=_ERR,
)
async def create_staff_user(
    body: CreateStaffUserRequest, actor: UserManager, db: Db
) -> Envelope[UserOut]:
    return ok(await AccessAdminService(db, actor).create_staff_user(body))


@router.get("/users/{user_id}", summary="Get a user", responses=_ERR)
async def get_user(user_id: uuid.UUID, actor: UserManager, db: Db) -> Envelope[UserOut]:
    return ok(await AccessAdminService(db, actor).get_user(user_id))


@router.patch(
    "/users/{user_id}/status",
    summary="Activate, suspend or disable a user",
    description="Suspending/disabling signs the user out everywhere.",
    responses=_ERR,
)
async def update_user_status(
    user_id: uuid.UUID, body: UpdateUserStatusRequest, actor: UserManager, db: Db
) -> Envelope[UserOut]:
    return ok(await AccessAdminService(db, actor).update_status(user_id, body.status, body.reason))


@router.post(
    "/users/{user_id}/roles",
    status_code=status.HTTP_201_CREATED,
    summary="Grant a role (optionally scoped)",
    description="Requires `role:manage`.",
    responses=_ERR,
)
async def assign_role(
    user_id: uuid.UUID, body: AssignRoleRequest, actor: RoleManager, db: Db
) -> Envelope[UserOut]:
    return ok(await AccessAdminService(db, actor).assign_role(user_id, body))


@router.delete(
    "/users/{user_id}/roles/{user_role_id}",
    summary="Revoke a role grant",
    description="Requires `role:manage`.",
    responses=_ERR,
)
async def revoke_role(
    user_id: uuid.UUID, user_role_id: uuid.UUID, actor: RoleManager, db: Db
) -> Envelope[UserOut]:
    return ok(await AccessAdminService(db, actor).revoke_role(user_id, user_role_id))


@router.get("/roles", summary="List roles with permissions", responses=_ERR)
async def list_roles(actor: RoleViewer, db: Db) -> Envelope[list[RoleOut]]:
    return ok(await AccessAdminService(db, actor).list_roles())


@router.put(
    "/roles/{role_code}/permissions",
    summary="Replace a role's permissions",
    description="Requires `role:manage`. SUPER_ADMIN is immutable.",
    responses=_ERR,
)
async def update_role_permissions(
    role_code: str, body: UpdateRolePermissionsRequest, actor: RoleManager, db: Db
) -> Envelope[RoleOut]:
    return ok(
        await AccessAdminService(db, actor).update_role_permissions(role_code, body.permissions)
    )


@router.get("/permissions", summary="List permission codes", responses=_ERR)
async def list_permissions(actor: RoleViewer, db: Db) -> Envelope[list[PermissionOut]]:
    return ok(await AccessAdminService(db, actor).list_permissions())
