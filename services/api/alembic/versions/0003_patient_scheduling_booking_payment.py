"""Patients, scheduling, coupons, bookings, and payments.

Adds schemas `patient`, `scheduling`, `coupon`, `booking`, and `payment`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for schema in ("patient", "scheduling", "coupon", "booking", "payment"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # --- PATIENT SCHEMA ---
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_code", sa.String(length=40), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("full_name_bn", sa.String(length=150), nullable=True),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(length=1), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("blood_group", sa.String(length=5), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint("sex IN ('M', 'F', 'O')", name="ck_patients_sex"),
        sa.CheckConstraint(
            "blood_group IS NULL OR blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')",
            name="ck_patients_blood_group",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_code"),
        schema="patient",
    )
    op.create_index("ix_patients_owner_user_id", "patients", ["owner_user_id"], schema="patient")
    op.create_index("ix_patients_phone", "patients", ["phone"], schema="patient")

    op.create_table(
        "family_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "relationship", sa.String(length=20), server_default=sa.text("'OTHER'"), nullable=False
        ),
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
        sa.CheckConstraint(
            "relationship IN ('SELF', 'FATHER', 'MOTHER', 'SPOUSE', 'CHILD', 'SIBLING', 'OTHER')",
            name="ck_family_links_relationship",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "patient_id", name="uq_family_links_user_patient"),
        schema="patient",
    )
    op.create_index("ix_family_links_user_id", "family_links", ["user_id"], schema="patient")
    op.create_index("ix_family_links_patient_id", "family_links", ["patient_id"], schema="patient")

    op.create_table(
        "addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=True),
        sa.Column("division_id", sa.Uuid(), nullable=True),
        sa.Column("district_id", sa.Uuid(), nullable=True),
        sa.Column("upazila_id", sa.Uuid(), nullable=True),
        sa.Column("area_id", sa.Uuid(), nullable=True),
        sa.Column("house", sa.String(length=100), nullable=False),
        sa.Column("road", sa.String(length=100), nullable=True),
        sa.Column("block", sa.String(length=50), nullable=True),
        sa.Column("landmark", sa.String(length=150), nullable=True),
        sa.Column("label", sa.String(length=20), server_default=sa.text("'HOME'"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.CheckConstraint("label IN ('HOME', 'WORK', 'OTHER')", name="ck_addresses_label"),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.patients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["division_id"], ["geo.divisions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["district_id"], ["geo.districts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["upazila_id"], ["geo.upazilas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["area_id"], ["geo.areas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="patient",
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"], schema="patient")
    op.create_index("ix_addresses_patient_id", "addresses", ["patient_id"], schema="patient")

    # --- SCHEDULING SCHEMA ---
    op.create_table(
        "slot_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("capacity", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("mode", sa.String(length=20), server_default=sa.text("'CENTRE'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("mode IN ('HOME', 'CENTRE')", name="ck_slot_templates_mode"),
        sa.CheckConstraint("owner_type IN ('CENTRE', 'ZONE')", name="ck_slot_templates_owner_type"),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_slot_templates_weekday"),
        sa.CheckConstraint("capacity > 0", name="ck_slot_templates_capacity"),
        sa.PrimaryKeyConstraint("id"),
        schema="scheduling",
    )
    op.create_index(
        "ix_slot_templates_owner",
        "slot_templates",
        ["owner_type", "owner_id"],
        schema="scheduling",
    )

    op.create_table(
        "slot_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("booked", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("held", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("mode IN ('HOME', 'CENTRE')", name="ck_slot_instances_mode"),
        sa.CheckConstraint("owner_type IN ('CENTRE', 'ZONE')", name="ck_slot_instances_owner_type"),
        sa.CheckConstraint("booked >= 0 AND held >= 0", name="ck_slot_instances_counts"),
        sa.CheckConstraint("booked + held <= capacity", name="ck_slot_instances_capacity"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_type",
            "owner_id",
            "date",
            "start_time",
            "mode",
            name="uq_slot_instances_owner_date_time_mode",
        ),
        schema="scheduling",
    )
    op.create_index("ix_slot_instances_date", "slot_instances", ["date"], schema="scheduling")
    op.create_index(
        "ix_slot_instances_owner",
        "slot_instances",
        ["owner_type", "owner_id", "date"],
        schema="scheduling",
    )

    op.create_table(
        "slot_holds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slot_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["slot_id"], ["scheduling.slot_instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="scheduling",
    )
    op.create_index("ix_slot_holds_slot_id", "slot_holds", ["slot_id"], schema="scheduling")
    op.create_index("ix_slot_holds_user_id", "slot_holds", ["user_id"], schema="scheduling")
    op.create_index("ix_slot_holds_expires_at", "slot_holds", ["expires_at"], schema="scheduling")

    # --- COUPON SCHEMA ---
    op.create_table(
        "coupons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False),
        sa.Column("max_discount", sa.BigInteger(), nullable=True),
        sa.Column("min_amount", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_user_limit", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "first_booking_only", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("type IN ('PERCENT', 'FIXED')", name="ck_coupons_type"),
        sa.CheckConstraint("value > 0", name="ck_coupons_value"),
        sa.CheckConstraint("min_amount >= 0", name="ck_coupons_min_amount"),
        sa.CheckConstraint(
            "max_discount IS NULL OR max_discount >= 0", name="ck_coupons_max_discount"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="coupon",
    )
    op.create_index("ix_coupons_code", "coupons", ["code"], schema="coupon")

    op.create_table(
        "coupon_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coupon_id", sa.Uuid(), nullable=False),
        sa.Column("rule_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "rule_type IN ('TEST', 'PACKAGE', 'CENTRE', 'CORPORATE', 'USER', 'CATEGORY')",
            name="ck_coupon_rules_type",
        ),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupon.coupons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="coupon",
    )
    op.create_index("ix_coupon_rules_coupon_id", "coupon_rules", ["coupon_id"], schema="coupon")

    op.create_table(
        "coupon_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coupon_id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(["coupon_id"], ["coupon.coupons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coupon_id", "booking_id", name="uq_coupon_usage_booking"),
        schema="coupon",
    )
    op.create_index(
        "ix_coupon_usage_coupon_user", "coupon_usage", ["coupon_id", "user_id"], schema="coupon"
    )

    # --- BOOKING SCHEMA ---
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_code", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("centre_id", sa.Uuid(), nullable=True),
        sa.Column("address_id", sa.Uuid(), nullable=True),
        sa.Column("slot_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status", sa.String(length=30), server_default=sa.text("'CREATED'"), nullable=False
        ),
        sa.Column("subtotal", sa.BigInteger(), nullable=False),
        sa.Column("discount", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("collection_fee", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("coupon_id", sa.Uuid(), nullable=True),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("corporate_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=20), server_default=sa.text("'WEB'"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("patient_notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
        sa.CheckConstraint("mode IN ('HOME', 'CENTRE')", name="ck_bookings_mode"),
        sa.CheckConstraint(
            "source IN ('WEB', 'CONSOLE', 'PARTNER', 'CORPORATE')", name="ck_bookings_source"
        ),
        sa.CheckConstraint("subtotal >= 0 AND total >= 0", name="ck_bookings_amounts"),
        sa.CheckConstraint(
            "total = subtotal - discount + collection_fee", name="ck_bookings_total_equation"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["centre_id"], ["centre.centres.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["address_id"], ["patient.addresses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["slot_id"], ["scheduling.slot_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupon.coupons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_code"),
        sa.UniqueConstraint("idempotency_key"),
        schema="booking",
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], schema="booking")
    op.create_index("ix_bookings_status", "bookings", ["status"], schema="booking")
    op.create_index("ix_bookings_slot_id", "bookings", ["slot_id"], schema="booking")
    op.create_index("ix_bookings_created_at", "bookings", ["created_at"], schema="booking")

    op.create_table(
        "booking_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("price_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("mrp_snapshot", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default=sa.text("'PENDING'"), nullable=False
        ),
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
        sa.CheckConstraint("item_type IN ('TEST', 'PACKAGE')", name="ck_booking_items_type"),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        schema="booking",
    )
    op.create_index(
        "ix_booking_items_booking_id", "booking_items", ["booking_id"], schema="booking"
    )
    op.create_index(
        "ix_booking_items_patient_id", "booking_items", ["patient_id"], schema="booking"
    )

    op.create_table(
        "booking_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="booking",
    )
    op.create_index(
        "ix_booking_status_history_booking_id",
        "booking_status_history",
        ["booking_id"],
        schema="booking",
    )

    # --- PAYMENT SCHEMA ---
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default=sa.text("'INITIATED'"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
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
        sa.CheckConstraint(
            "method IN ('ONLINE', 'CASH', 'BKASH', 'NAGAD', 'CARD')",
            name="ck_payments_method",
        ),
        sa.CheckConstraint(
            "provider IN ('SSLCOMMERZ', 'CASH', 'MANUAL')",
            name="ck_payments_provider",
        ),
        sa.CheckConstraint(
            "status IN ('INITIATED', 'PENDING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'REFUNDED', 'PARTIALLY_REFUNDED')",
            name="ck_payments_status",
        ),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount"),
        sa.ForeignKeyConstraint(["booking_id"], ["booking.bookings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        schema="payment",
    )
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"], schema="payment")
    op.create_index("ix_payments_status", "payments", ["status"], schema="payment")

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("provider_txn_id", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["payment_id"], ["payment.payments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_txn_id"),
        schema="payment",
    )
    op.create_index(
        "ix_payment_transactions_payment_id",
        "payment_transactions",
        ["payment_id"],
        schema="payment",
    )
    op.create_index(
        "ix_payment_transactions_provider_txn_id",
        "payment_transactions",
        ["provider_txn_id"],
        schema="payment",
    )

    op.create_table(
        "payment_callbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_txn_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_txn_id", "event_type", name="uq_payment_callbacks_txn_event"
        ),
        schema="payment",
    )
    op.create_index(
        "ix_payment_callbacks_provider_txn_id",
        "payment_callbacks",
        ["provider_txn_id"],
        schema="payment",
    )


def downgrade() -> None:
    for schema in ("payment", "booking", "coupon", "scheduling", "patient"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
