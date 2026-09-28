"""Baseline: module schemas, core outbox, auth (users/RBAC/sessions), append-only audit log.

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def _ts(name: str, *, nullable: bool = False, default: bool = True) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        name, sa.DateTime(timezone=True), nullable=nullable, server_default=NOW if default else None
    )


def upgrade() -> None:
    for schema in ("core", "auth", "audit"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ---------------------------------------------------------------- core
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(120), nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False),
        _ts("created_at"),
        _ts("published_at", nullable=True, default=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.String(500)),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_events"),
        schema="core",
    )
    op.create_index(
        "ix_outbox_events_unpublished",
        "outbox_events",
        ["created_at"],
        schema="core",
        postgresql_where=sa.text("published_at IS NULL"),
    )

    # ---------------------------------------------------------------- auth
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("phone", sa.String(16)),
        sa.Column("email", sa.String(254)),
        sa.Column("full_name", sa.String(150)),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferred_language", sa.String(2), nullable=False, server_default="en"),
        _ts("phone_verified_at", nullable=True, default=False),
        _ts("email_verified_at", nullable=True, default=False),
        _ts("last_login_at", nullable=True, default=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "phone IS NOT NULL OR email IS NOT NULL", name="ck_users_has_identifier"
        ),
        sa.CheckConstraint(r"phone ~ '^\+8801[3-9][0-9]{8}$'", name="ck_users_phone_format"),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'DISABLED')", name="ck_users_status_valid"
        ),
        schema="auth",
    )
    op.execute(
        "CREATE INDEX ix_users_full_name_trgm ON auth.users "
        "USING gin (lower(full_name) gin_trgm_ops)"
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        schema="auth",
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
        schema="auth",
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth.roles.id"],
            ondelete="CASCADE",
            name="fk_role_permissions_role_id_roles",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["auth.permissions.id"],
            ondelete="CASCADE",
            name="fk_role_permissions_permission_id_permissions",
        ),
        schema="auth",
    )
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(16), nullable=False, server_default="GLOBAL"),
        sa.Column("scope_id", sa.Uuid()),
        sa.Column("granted_by", sa.Uuid()),
        _ts("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["auth.users.id"], ondelete="CASCADE", name="fk_user_roles_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["auth.roles.id"], ondelete="RESTRICT", name="fk_user_roles_role_id_roles"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="fk_user_roles_granted_by_users",
        ),
        sa.UniqueConstraint(
            "user_id",
            "role_id",
            "scope_type",
            "scope_id",
            name="uq_user_roles_assignment",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "scope_type IN ('GLOBAL', 'BRANCH', 'LAB', 'CORPORATE', 'PARTNER')",
            name="ck_user_roles_scope_type_valid",
        ),
        sa.CheckConstraint(
            "(scope_type = 'GLOBAL') = (scope_id IS NULL)",
            name="ck_user_roles_scope_id_matches_type",
        ),
        schema="auth",
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], schema="auth")

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ip", sa.String(64)),
        _ts("created_at"),
        _ts("last_seen_at"),
        _ts("expires_at", default=False),
        _ts("revoked_at", nullable=True, default=False),
        sa.Column("revoke_reason", sa.String(40)),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["auth.users.id"], ondelete="CASCADE", name="fk_sessions_user_id_users"
        ),
        schema="auth",
    )
    op.create_index(
        "ix_sessions_user_active",
        "sessions",
        ["user_id"],
        schema="auth",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        _ts("created_at"),
        _ts("expires_at", default=False),
        _ts("used_at", nullable=True, default=False),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["auth.sessions.id"],
            ondelete="CASCADE",
            name="fk_refresh_tokens_session_id_sessions",
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        schema="auth",
    )
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"], schema="auth")

    # ---------------------------------------------------------------- audit
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        _ts("at"),
        sa.Column("actor_user_id", sa.Uuid()),
        sa.Column("actor_roles", pg.ARRAY(sa.String(40)), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("request_id", sa.String(64)),
        sa.Column("before", pg.JSONB()),
        sa.Column("after", pg.JSONB()),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        schema="audit",
    )
    op.create_index(
        "ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id", "at"], schema="audit"
    )
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_user_id", "at"], schema="audit")
    op.create_index("ix_audit_logs_at", "audit_logs", ["at"], schema="audit")

    # Audit rows are immutable for everyone, including the application role.
    op.execute("""
        CREATE FUNCTION audit.forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'audit.audit_logs is append-only (% blocked)', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER audit_logs_no_update_delete
        BEFORE UPDATE OR DELETE ON audit.audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit.forbid_mutation()
    """)
    op.execute("""
        CREATE TRIGGER audit_logs_no_truncate
        BEFORE TRUNCATE ON audit.audit_logs
        FOR EACH STATEMENT EXECUTE FUNCTION audit.forbid_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE")
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")
    op.drop_table("outbox_events", schema="core")
