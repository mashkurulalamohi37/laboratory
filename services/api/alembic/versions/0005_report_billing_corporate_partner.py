"""Reports, billing, corporate, and partner networks.

Adds schemas `report`, `billing`, `corporate`, and `partner`.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for schema in ("report", "billing", "corporate", "partner"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ==========================================
    # REPORT SCHEMA
    # ==========================================
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_code", sa.String(length=32), nullable=False),
        sa.Column("lab_order_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="FINAL", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_code", name="uq_reports_report_code"),
        schema="report",
    )
    op.create_index("ix_reports_patient_id", "reports", ["patient_id"], schema="report")
    op.create_index("ix_reports_lab_order_id", "reports", ["lab_order_id"], schema="report")

    op.create_table(
        "report_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), server_default="1", nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="FINAL", nullable=False),
        sa.Column("amend_reason", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["report.reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "version_no", name="uq_report_versions_version_no"),
        schema="report",
    )
    op.create_index("ix_report_versions_report_id", "report_versions", ["report_id"], schema="report")

    op.create_table(
        "report_signatures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("pathologist_id", sa.Uuid(), nullable=False),
        sa.Column("pathologist_name", sa.String(length=255), nullable=False),
        sa.Column("bmdc_number", sa.String(length=64), nullable=False),
        sa.Column("designation", sa.String(length=128), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("signature_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["report.report_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="report",
    )
    op.create_index("ix_report_signatures_version_id", "report_signatures", ["version_id"], schema="report")

    op.create_table(
        "report_verification_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["report.report_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_report_verification_tokens_token"),
        schema="report",
    )
    op.create_index("ix_report_verification_tokens_version_id", "report_verification_tokens", ["version_id"], schema="report")

    op.create_table(
        "report_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("share_token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("access_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["report.reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token", name="uq_report_shares_share_token"),
        schema="report",
    )
    op.create_index("ix_report_shares_report_id", "report_shares", ["report_id"], schema="report")

    # ==========================================
    # BILLING SCHEMA
    # ==========================================
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_no", sa.String(length=32), nullable=False),
        sa.Column("bill_to_type", sa.String(length=32), nullable=False),
        sa.Column("bill_to_id", sa.Uuid(), nullable=False),
        sa.Column("bill_to_name", sa.String(length=255), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("corporate_id", sa.Uuid(), nullable=True),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("subtotal", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("discount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("tax", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ISSUED", nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_no", name="uq_invoices_invoice_no"),
        schema="billing",
    )
    op.create_index("ix_invoices_bill_to", "invoices", ["bill_to_type", "bill_to_id"], schema="billing")
    op.create_index("ix_invoices_corporate_id", "invoices", ["corporate_id"], schema="billing")
    op.create_index("ix_invoices_partner_id", "invoices", ["partner_id"], schema="billing")
    op.create_index("ix_invoices_status", "invoices", ["status"], schema="billing")

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("item_type", sa.String(length=32), server_default="TEST", nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("unit_price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("total_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["billing.invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="billing",
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"], schema="billing")

    # ==========================================
    # CORPORATE SCHEMA
    # ==========================================
    op.create_table(
        "corporates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("contact_person", sa.String(length=128), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("credit_limit", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("credit_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_corporates_code"),
        schema="corporate",
    )

    op.create_table(
        "corporate_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("corporate_id", sa.Uuid(), nullable=False),
        sa.Column("contract_code", sa.String(length=64), nullable=False),
        sa.Column("price_list_id", sa.Uuid(), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), server_default="0.00", nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["corporate_id"], ["corporate.corporates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="corporate",
    )
    op.create_index("ix_corporate_contracts_corporate_id", "corporate_contracts", ["corporate_id"], schema="corporate")

    op.create_table(
        "corporate_employees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("corporate_id", sa.Uuid(), nullable=False),
        sa.Column("employee_code", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("designation", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["corporate_id"], ["corporate.corporates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("corporate_id", "employee_code", name="uq_corporate_employees_code"),
        schema="corporate",
    )
    op.create_index("ix_corporate_employees_corporate_id", "corporate_employees", ["corporate_id"], schema="corporate")
    op.create_index("ix_corporate_employees_patient_id", "corporate_employees", ["patient_id"], schema="corporate")

    # ==========================================
    # PARTNER SCHEMA
    # ==========================================
    op.create_table(
        "partners",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("centre_id", sa.Uuid(), nullable=True),
        sa.Column("commission_payout_type", sa.String(length=32), server_default="MONTHLY", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_partners_code"),
        schema="partner",
    )
    op.create_index("ix_partners_status", "partners", ["status"], schema="partner")

    op.create_table(
        "commission_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="ALL", nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("rule_type", sa.String(length=32), server_default="PERCENT", nullable=False),
        sa.Column("value", sa.Numeric(10, 2), server_default="10.00", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partner.partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="partner",
    )
    op.create_index("ix_commission_rules_partner_id", "commission_rules", ["partner_id"], schema="partner")

    op.create_table(
        "commission_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("gross_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("commission_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("net_amount", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partner.partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="partner",
    )
    op.create_index("ix_commission_entries_partner_id", "commission_entries", ["partner_id"], schema="partner")
    op.create_index("ix_commission_entries_booking_id", "commission_entries", ["booking_id"], schema="partner")
    op.create_index("ix_commission_entries_status", "commission_entries", ["status"], schema="partner")


def downgrade() -> None:
    for schema in ("partner", "corporate", "billing", "report"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
