"""Inventory, finance, CRM, and notifications.

Adds schemas `inventory`, `finance`, `crm`, and `notification`.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for schema in ("inventory", "finance", "crm", "notification"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ==========================================
    # INVENTORY SCHEMA
    # ==========================================
    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=32), nullable=False),
        sa.Column("current_stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_level", sa.Integer(), server_default="50", nullable=False),
        sa.Column("cost_per_unit", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("centre_id", sa.Uuid(), nullable=True),
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
        sa.UniqueConstraint("code", name="uq_inventory_items_code"),
        schema="inventory",
    )
    op.create_index(
        "ix_inventory_items_category", "items", ["category"], schema="inventory"
    )

    op.create_table(
        "batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("batch_no", sa.String(length=64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("initial_quantity", sa.Integer(), nullable=False),
        sa.Column("remaining_quantity", sa.Integer(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.ForeignKeyConstraint(
            ["item_id"], ["inventory.items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )
    op.create_index(
        "ix_stock_batches_item_id", "batches", ["item_id"], schema="inventory"
    )
    op.create_index(
        "ix_stock_batches_expiry", "batches", ["expiry_date"], schema="inventory"
    )

    op.create_table(
        "movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
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
            ["item_id"], ["inventory.items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["inventory.batches.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )
    op.create_index(
        "ix_stock_movements_item_id", "movements", ["item_id"], schema="inventory"
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("po_number", sa.String(length=32), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("total_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("po_number", name="uq_purchase_orders_po_number"),
        schema="inventory",
    )
    op.create_index(
        "ix_purchase_orders_status",
        "purchase_orders",
        ["status"],
        schema="inventory",
    )

    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("po_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_price", sa.BigInteger(), server_default="0", nullable=False),
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
            ["po_id"], ["inventory.purchase_orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["inventory.items.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )

    # ==========================================
    # FINANCE SCHEMA
    # ==========================================
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("voucher_no", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("centre_id", sa.Uuid(), nullable=True),
        sa.Column("paid_to", sa.String(length=255), nullable=False),
        sa.Column("payment_method", sa.String(length=32), server_default="CASH", nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("voucher_no", name="uq_expenses_voucher_no"),
        schema="finance",
    )
    op.create_index("ix_expenses_centre_id", "expenses", ["centre_id"], schema="finance")
    op.create_index("ix_expenses_category", "expenses", ["category"], schema="finance")
    op.create_index("ix_expenses_date", "expenses", ["expense_date"], schema="finance")

    op.create_table(
        "ar_ap_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("party_name", sa.String(length=255), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        schema="finance",
    )
    op.create_index("ix_ar_ap_type", "ar_ap_records", ["record_type"], schema="finance")
    op.create_index("ix_ar_ap_status", "ar_ap_records", ["status"], schema="finance")

    # ==========================================
    # CRM SCHEMA
    # ==========================================
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_no", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("patient_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), server_default="GENERAL", nullable=False),
        sa.Column("priority", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("ticket_no", name="uq_support_tickets_ticket_no"),
        schema="crm",
    )
    op.create_index("ix_support_tickets_status", "tickets", ["status"], schema="crm")
    op.create_index("ix_support_tickets_category", "tickets", ["category"], schema="crm")
    op.create_index("ix_support_tickets_user_id", "tickets", ["user_id"], schema="crm")

    op.create_table(
        "ticket_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("sender_name", sa.String(length=255), nullable=False),
        sa.Column("is_staff", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["ticket_id"], ["crm.tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="crm",
    )
    op.create_index(
        "ix_ticket_messages_ticket_id",
        "ticket_messages",
        ["ticket_id"],
        schema="crm",
    )

    # ==========================================
    # NOTIFICATION SCHEMA
    # ==========================================
    op.create_table(
        "templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), server_default="SMS", nullable=False),
        sa.Column("language", sa.String(length=16), server_default="BN", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
            "code",
            "channel",
            "language",
            name="uq_notification_templates_code_chan_lang",
        ),
        schema="notification",
    )
    op.create_index(
        "ix_notification_templates_code", "templates", ["code"], schema="notification"
    )

    op.create_table(
        "logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("template_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="SENT", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "dispatched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.PrimaryKeyConstraint("id"),
        schema="notification",
    )
    op.create_index(
        "ix_notification_logs_recipient", "logs", ["recipient"], schema="notification"
    )
    op.create_index(
        "ix_notification_logs_status", "logs", ["status"], schema="notification"
    )


def downgrade() -> None:
    for schema in ("notification", "crm", "finance", "inventory"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
