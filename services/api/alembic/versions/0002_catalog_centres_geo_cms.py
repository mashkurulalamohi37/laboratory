"""Catalog, centres, BD geography and CMS basics.

Adds schemas `geo`, `centre`, `catalog` and `cms`, the btree_gist extension, and two
exclusion constraints that autogenerate cannot express:

- reference ranges may not overlap (age band x effective dates) for identical criteria;
- a price list may hold only one price per item at any instant.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NIL_UUID = "'00000000-0000-0000-0000-000000000000'::uuid"


def upgrade() -> None:
    for schema in ("geo", "centre", "catalog", "cms"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["catalog.categories.id"],
            name=op.f("fk_categories_parent_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_categories_slug")),
        schema="catalog",
    )
    op.create_index(
        "ix_categories_parent_id", "categories", ["parent_id"], unique=False, schema="catalog"
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
        schema="catalog",
    )
    op.create_table(
        "health_concerns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_bn", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=40), server_default="activity", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("seo_title", sa.String(length=70), nullable=True),
        sa.Column("seo_description", sa.String(length=170), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple', coalesce(name, '')), 'A') || setweight(to_tsvector('simple', coalesce(description, '')), 'C')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_concerns")),
        sa.UniqueConstraint("slug", name=op.f("uq_health_concerns_slug")),
        schema="catalog",
    )
    op.create_index(
        "ix_health_concerns_search_vector",
        "health_concerns",
        ["search_vector"],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
    )
    op.create_table(
        "packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_bn", sa.String(length=200), nullable=True),
        sa.Column("aliases", sa.String(length=500), nullable=True),
        sa.Column("short_description", sa.String(length=300), nullable=True),
        sa.Column("short_description_bn", sa.String(length=300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_bn", sa.Text(), nullable=True),
        sa.Column("sex", sa.String(length=1), nullable=True),
        sa.Column("age_min_years", sa.SmallInteger(), nullable=True),
        sa.Column("age_max_years", sa.SmallInteger(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("popularity", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("seo_title", sa.String(length=70), nullable=True),
        sa.Column("seo_description", sa.String(length=170), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple', coalesce(name, '')), 'A') || setweight(to_tsvector('simple', coalesce(code, '')), 'A') || setweight(to_tsvector('simple', coalesce(aliases, '')), 'A') || setweight(to_tsvector('simple', coalesce(short_description, '')), 'C')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("sex IS NULL OR sex IN ('M', 'F')", name=op.f("ck_packages_sex_valid")),
        sa.CheckConstraint(
            "age_min_years IS NULL OR age_max_years IS NULL OR age_min_years <= age_max_years",
            name=op.f("ck_packages_age_band_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_packages")),
        sa.UniqueConstraint("code", name=op.f("uq_packages_code")),
        sa.UniqueConstraint("slug", name=op.f("uq_packages_slug")),
        schema="catalog",
    )
    op.create_index(
        "ix_packages_name_trgm",
        "packages",
        [sa.literal_column("lower(name)").label("lower_name")],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
        postgresql_ops={"lower_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_packages_search_vector",
        "packages",
        ["search_vector"],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
    )
    op.create_table(
        "preparations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("title_bn", sa.String(length=150), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("instructions_bn", sa.Text(), nullable=True),
        sa.Column("fasting_hours", sa.SmallInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint(
            "fasting_hours IS NULL OR fasting_hours BETWEEN 0 AND 24",
            name=op.f("ck_preparations_fasting"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_preparations")),
        sa.UniqueConstraint("code", name=op.f("uq_preparations_code")),
        schema="catalog",
    )
    op.create_table(
        "sample_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=True),
        sa.Column("container", sa.String(length=120), nullable=True),
        sa.Column("tube_colour", sa.String(length=40), nullable=True),
        sa.Column("default_volume_ml", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sample_types")),
        sa.UniqueConstraint("code", name=op.f("uq_sample_types_code")),
        schema="catalog",
    )
    op.create_table(
        "search_synonyms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("term", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=10), nullable=False),
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
            "target_type IN ('TEST', 'PACKAGE', 'CONCERN')",
            name=op.f("ck_search_synonyms_target_type_valid"),
        ),
        sa.CheckConstraint("term = lower(term)", name=op.f("ck_search_synonyms_term_lowercase")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_synonyms")),
        sa.UniqueConstraint("term", "target_type", "target_id", name="uq_search_synonyms_target"),
        schema="catalog",
    )
    op.create_index(
        "ix_search_synonyms_target",
        "search_synonyms",
        ["target_type", "target_id"],
        unique=False,
        schema="catalog",
    )
    op.create_index(
        "ix_search_synonyms_term_trgm",
        "search_synonyms",
        ["term"],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
        postgresql_ops={"term": "gin_trgm_ops"},
    )
    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_bn", sa.String(length=150), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branches")),
        sa.UniqueConstraint("code", name=op.f("uq_branches_code")),
        schema="centre",
    )
    op.create_table(
        "banners",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("placement", sa.String(length=12), server_default="HOME_HERO", nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("title_bn", sa.String(length=120), nullable=True),
        sa.Column("body", sa.String(length=300), nullable=True),
        sa.Column("body_bn", sa.String(length=300), nullable=True),
        sa.Column("cta_label", sa.String(length=40), nullable=True),
        sa.Column("cta_label_bn", sa.String(length=40), nullable=True),
        sa.Column("cta_href", sa.String(length=300), nullable=True),
        sa.Column("tone", sa.String(length=10), server_default="brand", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("unpublish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="DRAFT", nullable=False),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "placement IN ('HOME_HERO', 'HOME_STRIP')", name=op.f("ck_banners_placement_valid")
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name=op.f("ck_banners_status_valid")
        ),
        sa.CheckConstraint(
            "tone IN ('brand', 'accent', 'neutral')", name=op.f("ck_banners_tone_valid")
        ),
        sa.CheckConstraint(
            "unpublish_at IS NULL OR publish_at IS NULL OR unpublish_at > publish_at",
            name=op.f("ck_banners_window_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_banners")),
        schema="cms",
    )
    op.create_index(
        "ix_banners_placement_status",
        "banners",
        ["placement", "status"],
        unique=False,
        schema="cms",
    )
    op.create_table(
        "faqs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=40), server_default="general", nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("question_bn", sa.String(length=300), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answer_bn", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="DRAFT", nullable=False),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name=op.f("ck_faqs_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_faqs")),
        schema="cms",
    )
    op.create_index(
        "ix_faqs_category", "faqs", ["category", "sort_order"], unique=False, schema="cms"
    )
    op.create_table(
        "pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("title_bn", sa.String(length=150), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_bn", sa.Text(), nullable=True),
        sa.Column("seo_description", sa.String(length=170), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="DRAFT", nullable=False),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name=op.f("ck_pages_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pages")),
        sa.UniqueConstraint("slug", name=op.f("uq_pages_slug")),
        schema="cms",
    )
    op.create_table(
        "divisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divisions")),
        sa.UniqueConstraint("code", name=op.f("uq_divisions_code")),
        schema="geo",
    )
    op.create_table(
        "concern_packages",
        sa.Column("concern_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["concern_id"],
            ["catalog.health_concerns.id"],
            name=op.f("fk_concern_packages_concern_id_health_concerns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["catalog.packages.id"],
            name=op.f("fk_concern_packages_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("concern_id", "package_id", name=op.f("pk_concern_packages")),
        schema="catalog",
    )
    op.create_index(
        "ix_concern_packages_package_id",
        "concern_packages",
        ["package_id"],
        unique=False,
        schema="catalog",
    )
    op.create_table(
        "price_lists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["centre.branches.id"],
            name=op.f("fk_price_lists_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_lists")),
        sa.UniqueConstraint(
            "branch_id", name="uq_price_lists_branch_id", postgresql_nulls_not_distinct=True
        ),
        sa.UniqueConstraint("code", name=op.f("uq_price_lists_code")),
        schema="catalog",
    )
    op.create_table(
        "tests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_bn", sa.String(length=200), nullable=True),
        sa.Column("aliases", sa.String(length=500), nullable=True),
        sa.Column("short_description", sa.String(length=300), nullable=True),
        sa.Column("short_description_bn", sa.String(length=300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_bn", sa.Text(), nullable=True),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("sample_type_id", sa.Uuid(), nullable=False),
        sa.Column("sample_volume", sa.String(length=40), nullable=True),
        sa.Column("preparation_id", sa.Uuid(), nullable=True),
        sa.Column("tat_hours", sa.Integer(), nullable=False),
        sa.Column("home_collection", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "centre_collection", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("popularity", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("seo_title", sa.String(length=70), nullable=True),
        sa.Column("seo_description", sa.String(length=170), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple', coalesce(name, '')), 'A') || setweight(to_tsvector('simple', coalesce(code, '')), 'A') || setweight(to_tsvector('simple', coalesce(aliases, '')), 'A') || setweight(to_tsvector('simple', coalesce(short_description, '')), 'C')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint(
            "home_collection OR centre_collection", name=op.f("ck_tests_has_collection_mode")
        ),
        sa.CheckConstraint("tat_hours > 0", name=op.f("ck_tests_tat_positive")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["catalog.categories.id"],
            name=op.f("fk_tests_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["catalog.departments.id"],
            name=op.f("fk_tests_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["preparation_id"],
            ["catalog.preparations.id"],
            name=op.f("fk_tests_preparation_id_preparations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sample_type_id"],
            ["catalog.sample_types.id"],
            name=op.f("fk_tests_sample_type_id_sample_types"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tests")),
        sa.UniqueConstraint("code", name=op.f("uq_tests_code")),
        sa.UniqueConstraint("slug", name=op.f("uq_tests_slug")),
        schema="catalog",
    )
    op.create_index(
        "ix_tests_category_id", "tests", ["category_id"], unique=False, schema="catalog"
    )
    op.create_index(
        "ix_tests_department_id", "tests", ["department_id"], unique=False, schema="catalog"
    )
    op.create_index(
        "ix_tests_name_trgm",
        "tests",
        [sa.literal_column("lower(name)").label("lower_name")],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
        postgresql_ops={"lower_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_tests_search_vector",
        "tests",
        ["search_vector"],
        unique=False,
        schema="catalog",
        postgresql_using="gin",
    )
    op.create_table(
        "holidays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_bn", sa.String(length=150), nullable=True),
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
            ["branch_id"],
            ["centre.branches.id"],
            name=op.f("fk_holidays_branch_id_branches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_holidays")),
        sa.UniqueConstraint("branch_id", "date", name="uq_holidays_branch_date"),
        schema="centre",
    )
    op.create_table(
        "labs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_bn", sa.String(length=150), nullable=True),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["centre.branches.id"],
            name=op.f("fk_labs_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labs")),
        sa.UniqueConstraint("code", name=op.f("uq_labs_code")),
        schema="centre",
    )
    op.create_index("ix_labs_branch_id", "labs", ["branch_id"], unique=False, schema="centre")
    op.create_table(
        "districts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("division_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=False),
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
            ["division_id"],
            ["geo.divisions.id"],
            name=op.f("fk_districts_division_id_divisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_districts")),
        sa.UniqueConstraint("code", name=op.f("uq_districts_code")),
        schema="geo",
    )
    op.create_index(
        "ix_districts_division_id", "districts", ["division_id"], unique=False, schema="geo"
    )
    op.create_table(
        "concern_tests",
        sa.Column("concern_id", sa.Uuid(), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["concern_id"],
            ["catalog.health_concerns.id"],
            name=op.f("fk_concern_tests_concern_id_health_concerns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_id"],
            ["catalog.tests.id"],
            name=op.f("fk_concern_tests_test_id_tests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("concern_id", "test_id", name=op.f("pk_concern_tests")),
        schema="catalog",
    )
    op.create_index(
        "ix_concern_tests_test_id", "concern_tests", ["test_id"], unique=False, schema="catalog"
    )
    op.create_table(
        "package_tests",
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["catalog.packages.id"],
            name=op.f("fk_package_tests_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_id"],
            ["catalog.tests.id"],
            name=op.f("fk_package_tests_test_id_tests"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("package_id", "test_id", name=op.f("pk_package_tests")),
        schema="catalog",
    )
    op.create_index(
        "ix_package_tests_test_id", "package_tests", ["test_id"], unique=False, schema="catalog"
    )
    op.create_table(
        "price_list_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("price_list_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=10), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=True),
        sa.Column("package_id", sa.Uuid(), nullable=True),
        sa.Column("mrp", sa.BigInteger(), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(item_type = 'TEST' AND test_id IS NOT NULL AND package_id IS NULL) OR (item_type = 'PACKAGE' AND package_id IS NOT NULL AND test_id IS NULL)",
            name=op.f("ck_price_list_items_item_ref_matches_type"),
        ),
        sa.CheckConstraint(
            "item_type IN ('TEST', 'PACKAGE')", name=op.f("ck_price_list_items_item_type_valid")
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name=op.f("ck_price_list_items_effective_window"),
        ),
        sa.CheckConstraint(
            "price >= 0 AND mrp >= 0 AND price <= mrp",
            name=op.f("ck_price_list_items_amounts_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["catalog.packages.id"],
            name=op.f("fk_price_list_items_package_id_packages"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["price_list_id"],
            ["catalog.price_lists.id"],
            name=op.f("fk_price_list_items_price_list_id_price_lists"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_id"],
            ["catalog.tests.id"],
            name=op.f("fk_price_list_items_test_id_tests"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_list_items")),
        schema="catalog",
    )
    op.create_index(
        "ix_price_list_items_package",
        "price_list_items",
        ["price_list_id", "package_id", "effective_from"],
        unique=False,
        schema="catalog",
    )
    op.create_index(
        "ix_price_list_items_test",
        "price_list_items",
        ["price_list_id", "test_id", "effective_from"],
        unique=False,
        schema="catalog",
    )
    op.create_table(
        "test_parameters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_bn", sa.String(length=150), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("result_type", sa.String(length=12), server_default="NUMERIC", nullable=False),
        sa.Column("decimals", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("formula", sa.String(length=300), nullable=True),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("loinc", sa.String(length=20), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
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
        sa.CheckConstraint(
            "(result_type = 'CALCULATED') = (formula IS NOT NULL)",
            name=op.f("ck_test_parameters_formula_iff_calculated"),
        ),
        sa.CheckConstraint(
            "result_type IN ('NUMERIC', 'TEXT', 'OPTION', 'CALCULATED')",
            name=op.f("ck_test_parameters_result_type_valid"),
        ),
        sa.CheckConstraint(
            "decimals BETWEEN 0 AND 6", name=op.f("ck_test_parameters_decimals_range")
        ),
        sa.ForeignKeyConstraint(
            ["test_id"],
            ["catalog.tests.id"],
            name=op.f("fk_test_parameters_test_id_tests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_parameters")),
        sa.UniqueConstraint("test_id", "code", name="uq_test_parameters_test_code"),
        schema="catalog",
    )
    op.create_table(
        "upazilas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("district_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=False),
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
            ["district_id"],
            ["geo.districts.id"],
            name=op.f("fk_upazilas_district_id_districts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_upazilas")),
        sa.UniqueConstraint("code", name=op.f("uq_upazilas_code")),
        schema="geo",
    )
    op.create_index(
        "ix_upazilas_district_id", "upazilas", ["district_id"], unique=False, schema="geo"
    )
    op.create_table(
        "reference_ranges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parameter_id", sa.Uuid(), nullable=False),
        sa.Column("sex", sa.String(length=1), nullable=True),
        sa.Column("age_min_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("age_max_days", sa.Integer(), nullable=True),
        sa.Column("sample_type_id", sa.Uuid(), nullable=True),
        sa.Column("lab_id", sa.Uuid(), nullable=True),
        sa.Column("method", sa.String(length=80), nullable=True),
        sa.Column("low", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("high", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("critical_low", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("critical_high", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("text_normal", sa.String(length=120), nullable=True),
        sa.Column(
            "effective_from", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False
        ),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=300), nullable=True),
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
        sa.CheckConstraint(
            "sex IS NULL OR sex IN ('M', 'F')", name=op.f("ck_reference_ranges_sex_valid")
        ),
        sa.CheckConstraint(
            "age_max_days IS NULL OR age_max_days > age_min_days",
            name=op.f("ck_reference_ranges_age_band_valid"),
        ),
        sa.CheckConstraint(
            "age_min_days >= 0", name=op.f("ck_reference_ranges_age_min_nonnegative")
        ),
        sa.CheckConstraint(
            "critical_high IS NULL OR high IS NULL OR critical_high >= high",
            name=op.f("ck_reference_ranges_critical_high_ge_high"),
        ),
        sa.CheckConstraint(
            "critical_low IS NULL OR low IS NULL OR critical_low <= low",
            name=op.f("ck_reference_ranges_critical_low_le_low"),
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name=op.f("ck_reference_ranges_effective_window"),
        ),
        sa.CheckConstraint(
            "low IS NOT NULL OR high IS NOT NULL OR text_normal IS NOT NULL",
            name=op.f("ck_reference_ranges_has_normal"),
        ),
        sa.CheckConstraint(
            "low IS NULL OR high IS NULL OR low <= high",
            name=op.f("ck_reference_ranges_low_le_high"),
        ),
        sa.ForeignKeyConstraint(
            ["lab_id"],
            ["centre.labs.id"],
            name=op.f("fk_reference_ranges_lab_id_labs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parameter_id"],
            ["catalog.test_parameters.id"],
            name=op.f("fk_reference_ranges_parameter_id_test_parameters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sample_type_id"],
            ["catalog.sample_types.id"],
            name=op.f("fk_reference_ranges_sample_type_id_sample_types"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reference_ranges")),
        schema="catalog",
    )
    op.create_index(
        "ix_reference_ranges_parameter_id",
        "reference_ranges",
        ["parameter_id"],
        unique=False,
        schema="catalog",
    )
    op.create_table(
        "areas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("upazila_id", sa.Uuid(), nullable=False),
        sa.Column("postcode", sa.String(length=8), nullable=True),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_bn", sa.String(length=120), nullable=False),
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
            ["upazila_id"],
            ["geo.upazilas.id"],
            name=op.f("fk_areas_upazila_id_upazilas"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_areas")),
        sa.UniqueConstraint("code", name=op.f("uq_areas_code")),
        schema="geo",
    )
    op.create_index("ix_areas_upazila_id", "areas", ["upazila_id"], unique=False, schema="geo")
    op.create_table(
        "centres",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_bn", sa.String(length=150), nullable=True),
        sa.Column("type", sa.String(length=20), server_default="BRANCH_CENTRE", nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("lab_id", sa.Uuid(), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("address_bn", sa.String(length=300), nullable=True),
        sa.Column("landmark", sa.String(length=200), nullable=True),
        sa.Column("district_id", sa.Uuid(), nullable=False),
        sa.Column("upazila_id", sa.Uuid(), nullable=True),
        sa.Column("area_id", sa.Uuid(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("phone", sa.String(length=16), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column(
            "services",
            postgresql.ARRAY(sa.String(length=30)),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_bn", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "type IN ('BRANCH_CENTRE', 'COLLECTION_POINT', 'PARTNER')",
            name=op.f("ck_centres_type_valid"),
        ),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name=op.f("ck_centres_latitude_range")),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180", name=op.f("ck_centres_longitude_range")
        ),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["geo.areas.id"],
            name=op.f("fk_centres_area_id_areas"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["centre.branches.id"],
            name=op.f("fk_centres_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["geo.districts.id"],
            name=op.f("fk_centres_district_id_districts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lab_id"], ["centre.labs.id"], name=op.f("fk_centres_lab_id_labs"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["upazila_id"],
            ["geo.upazilas.id"],
            name=op.f("fk_centres_upazila_id_upazilas"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_centres")),
        sa.UniqueConstraint("code", name=op.f("uq_centres_code")),
        sa.UniqueConstraint("slug", name=op.f("uq_centres_slug")),
        schema="centre",
    )
    op.create_index("ix_centres_area_id", "centres", ["area_id"], unique=False, schema="centre")
    op.create_index("ix_centres_branch_id", "centres", ["branch_id"], unique=False, schema="centre")
    op.create_index(
        "ix_centres_district_id", "centres", ["district_id"], unique=False, schema="centre"
    )
    op.create_index(
        "ix_centres_name_trgm",
        "centres",
        [sa.literal_column("lower(name)").label("lower_name")],
        unique=False,
        schema="centre",
        postgresql_using="gin",
        postgresql_ops={"lower_name": "gin_trgm_ops"},
    )
    op.create_table(
        "centre_hours",
        sa.Column("centre_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=False),
        sa.Column("closes_at", sa.Time(), nullable=False),
        sa.CheckConstraint(
            "opens_at < closes_at", name=op.f("ck_centre_hours_opens_before_closes")
        ),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_centre_hours_weekday_range")),
        sa.ForeignKeyConstraint(
            ["centre_id"],
            ["centre.centres.id"],
            name=op.f("fk_centre_hours_centre_id_centres"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("centre_id", "weekday", "opens_at", name=op.f("pk_centre_hours")),
        schema="centre",
    )

    # Same criteria + overlapping age band + overlapping validity = ambiguous match.
    op.execute(f"""
        ALTER TABLE catalog.reference_ranges
        ADD CONSTRAINT ex_reference_ranges_no_overlap EXCLUDE USING gist (
            parameter_id WITH =,
            (coalesce(sex, '*')) WITH =,
            (coalesce(sample_type_id, {NIL_UUID})) WITH =,
            (coalesce(lab_id, {NIL_UUID})) WITH =,
            (lower(coalesce(method, ''))) WITH =,
            (int4range(age_min_days, age_max_days, '[)')) WITH &&,
            (daterange(effective_from, effective_to, '[)')) WITH &&
        )
    """)
    op.execute("""
        ALTER TABLE catalog.price_list_items
        ADD CONSTRAINT ex_price_list_items_no_overlap EXCLUDE USING gist (
            price_list_id WITH =,
            item_type WITH =,
            (coalesce(test_id, package_id)) WITH =,
            (tstzrange(effective_from, effective_to, '[)')) WITH &&
        )
    """)


def downgrade() -> None:
    for schema in ("cms", "catalog", "centre", "geo"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
