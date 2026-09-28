"""Auth schema: identities, credentials, sessions, refresh tokens and RBAC."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "auth"


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("phone IS NOT NULL OR email IS NOT NULL", name="has_identifier"),
        CheckConstraint(r"phone ~ '^\+8801[3-9][0-9]{8}$'", name="phone_format"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'DISABLED')", name="status_valid"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    phone: Mapped[str | None] = mapped_column(String(16), unique=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(150))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    preferred_language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="en")
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user", lazy="raise", foreign_keys="UserRole.user_id"
    )


# Trigram index for console name search; opclass via postgresql_ops so Alembic can compare it.
Index(
    "ix_users_full_name_trgm",
    func.lower(User.full_name).label("lower_full_name"),
    postgresql_using="gin",
    postgresql_ops={"lower_full_name": "gin_trgm_ops"},
)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[UUIDPk]
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    permissions: Mapped[list[Permission]] = relationship(
        secondary=f"{SCHEMA}.role_permissions", lazy="raise"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": SCHEMA}

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role_id",
            "scope_type",
            "scope_id",
            name="uq_user_roles_assignment",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "scope_type IN ('GLOBAL', 'BRANCH', 'LAB', 'CORPORATE', 'PARTNER')",
            name="scope_type_valid",
        ),
        CheckConstraint(
            "(scope_type = 'GLOBAL') = (scope_id IS NULL)", name="scope_id_matches_type"
        ),
        Index("ix_user_roles_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.roles.id", ondelete="RESTRICT"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="GLOBAL")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id], lazy="raise")
    role: Mapped[Role] = relationship(lazy="joined")


class Session(Base):
    """A login on one device. Doubles as the refresh-token family."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", postgresql_where=text("revoked_at IS NULL")),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(40))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_session_id", "session_id"), {"schema": SCHEMA})

    id: Mapped[UUIDPk]
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{SCHEMA}.sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
