"""Collection, samples, lab orders, results, and critical alerts.

Adds schemas `collection`, `sample`, `lab`, and `result`.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for schema in ("collection", "sample", "lab", "result"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ==========================================
    # COLLECTION SCHEMA
    # ==========================================
    op.create_table(
        "collectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("daily_capacity", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("vehicle_type", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["centre.branches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        schema="collection",
    )

    op.create_table(
        "collection_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("collector_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("slot_id", sa.Uuid(), nullable=True),
        sa.Column("verification_code", sa.String(length=6), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("patient_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collector_id"], ["collection.collectors.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["slot_id"], ["scheduling.slot_instances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", name="uq_collection_assignment_booking"),
        schema="collection",
    )
    op.create_index(
        "ix_collection_assignments_collector",
        "collection_assignments",
        ["collector_id", "scheduled_date"],
        schema="collection",
    )

    op.create_table(
        "collection_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["collection.collection_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="collection",
    )

    # ==========================================
    # SAMPLE SCHEMA
    # ==========================================
    op.create_table(
        "sample_rejection_reasons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_bn", sa.String(length=255), nullable=False),
        sa.Column("requires_recollection", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="sample",
    )

    op.create_table(
        "samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("booking_item_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("sample_type_id", sa.Uuid(), nullable=False),
        sa.Column("container", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CREATED"),
        sa.Column("collected_by", sa.Uuid(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collection_centre_id", sa.Uuid(), nullable=True),
        sa.Column("lab_id", sa.Uuid(), nullable=True),
        sa.Column("rejection_reason_id", sa.Uuid(), nullable=True),
        sa.Column("rejection_notes", sa.Text(), nullable=True),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["booking_item_id"], ["booking.booking_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sample_type_id"], ["catalog.sample_types.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["collected_by"], ["auth.users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["collection_centre_id"], ["centre.centres.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["lab_id"], ["centre.labs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["rejection_reason_id"], ["sample.sample_rejection_reasons.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["parent_sample_id"], ["sample.samples.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode", name="uq_samples_barcode"),
        schema="sample",
    )
    op.create_index("ix_samples_booking", "samples", ["booking_id"], schema="sample")
    op.create_index("ix_samples_barcode", "samples", ["barcode"], schema="sample")

    op.create_table(
        "sample_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("location_type", sa.String(length=32), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.samples.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="sample",
    )

    op.create_table(
        "sample_transfers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manifest_code", sa.String(length=64), nullable=False),
        sa.Column("source_centre_id", sa.Uuid(), nullable=False),
        sa.Column("destination_lab_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DISPATCHED"),
        sa.Column("dispatched_by", sa.Uuid(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_by", sa.Uuid(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("temperature_celsius", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_centre_id"], ["centre.centres.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destination_lab_id"], ["centre.labs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dispatched_by"], ["auth.users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_code", name="uq_sample_transfers_manifest"),
        schema="sample",
    )

    op.create_table(
        "sample_transfer_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transfer_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["transfer_id"], ["sample.sample_transfers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.samples.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transfer_id", "sample_id", name="uq_transfer_sample"),
        schema="sample",
    )

    # ==========================================
    # LAB SCHEMA
    # ==========================================
    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("lab_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="ROUTINE"),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lab_id"], ["centre.labs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no", name="uq_lab_orders_order_no"),
        schema="lab",
    )
    op.create_index("ix_lab_orders_booking", "lab_orders", ["booking_id"], schema="lab")

    op.create_table(
        "lab_order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lab_order_id", sa.Uuid(), nullable=False),
        sa.Column("booking_item_id", sa.Uuid(), nullable=True),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=True),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lab_order_id"], ["lab.lab_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["booking_item_id"], ["booking.booking_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["test_id"], ["catalog.tests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.samples.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["department_id"], ["catalog.departments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="lab",
    )

    # ==========================================
    # RESULT SCHEMA
    # ==========================================
    op.create_table(
        "results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lab_order_item_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("entered_by", sa.Uuid(), nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amended_by", sa.Uuid(), nullable=True),
        sa.Column("amended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amend_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lab_order_item_id"], ["lab.lab_order_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["entered_by"], ["auth.users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_by"], ["auth.users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["amended_by"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lab_order_item_id", "version", name="uq_result_item_version"),
        schema="result",
    )

    op.create_table(
        "result_parameters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("parameter_id", sa.Uuid(), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_option", sa.String(length=128), nullable=True),
        sa.Column("unit_snapshot", sa.String(length=32), nullable=True),
        sa.Column("ref_range_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("flag", sa.String(length=16), nullable=False, server_default="N"),
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("delta_check_alert", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["result_id"], ["result.results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parameter_id"], ["catalog.test_parameters.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="result",
    )

    op.create_table(
        "result_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("comment_type", sa.String(length=32), nullable=False, server_default="CLINICAL"),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["result_id"], ["result.results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["auth.users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        schema="result",
    )

    op.create_table(
        "critical_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("result_parameter_id", sa.Uuid(), nullable=False),
        sa.Column("lab_order_item_id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="TRIGGERED"),
        sa.Column("notified_users", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["result_parameter_id"], ["result.result_parameters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["lab_order_item_id"], ["lab.lab_order_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="result",
    )


def downgrade() -> None:
    op.drop_table("critical_alerts", schema="result")
    op.drop_table("result_comments", schema="result")
    op.drop_table("result_parameters", schema="result")
    op.drop_table("results", schema="result")

    op.drop_table("lab_order_items", schema="lab")
    op.drop_table("lab_orders", schema="lab")

    op.drop_table("sample_transfer_items", schema="sample")
    op.drop_table("sample_transfers", schema="sample")
    op.drop_table("sample_events", schema="sample")
    op.drop_table("samples", schema="sample")
    op.drop_table("sample_rejection_reasons", schema="sample")

    op.drop_table("collection_events", schema="collection")
    op.drop_table("collection_assignments", schema="collection")
    op.drop_table("collectors", schema="collection")

    for schema in ("result", "lab", "sample", "collection"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
