"""CMS basics: banners, static pages and FAQs, each with draft/publish workflow.

Bodies are stored as a restricted Markdown subset and rendered by the web app without
HTML passthrough, so CMS content cannot inject markup or scripts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDPk

SCHEMA = "cms"

STATUSES = ("DRAFT", "PUBLISHED", "ARCHIVED")
BANNER_PLACEMENTS = ("HOME_HERO", "HOME_STRIP")
BANNER_TONES = ("brand", "accent", "neutral")


class _Publishable:
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="DRAFT")
    #: Visible from this instant when PUBLISHED (NULL = immediately).
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class Banner(_Publishable, TimestampMixin, Base):
    __tablename__ = "banners"
    __table_args__ = (
        CheckConstraint(f"status IN {STATUSES}", name="status_valid"),
        CheckConstraint(f"placement IN {BANNER_PLACEMENTS}", name="placement_valid"),
        CheckConstraint(f"tone IN {BANNER_TONES}", name="tone_valid"),
        CheckConstraint(
            "unpublish_at IS NULL OR publish_at IS NULL OR unpublish_at > publish_at",
            name="window_valid",
        ),
        Index("ix_banners_placement_status", "placement", "status"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    placement: Mapped[str] = mapped_column(String(12), nullable=False, server_default="HOME_HERO")
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    title_bn: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[str | None] = mapped_column(String(300))
    body_bn: Mapped[str | None] = mapped_column(String(300))
    cta_label: Mapped[str | None] = mapped_column(String(40))
    cta_label_bn: Mapped[str | None] = mapped_column(String(40))
    #: Internal path ("/packages/…") or an https URL; validated by the API schema.
    cta_href: Mapped[str | None] = mapped_column(String(300))
    tone: Mapped[str] = mapped_column(String(10), nullable=False, server_default="brand")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    unpublish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Page(_Publishable, TimestampMixin, Base):
    __tablename__ = "pages"
    __table_args__ = (
        CheckConstraint(f"status IN {STATUSES}", name="status_valid"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    title_bn: Mapped[str | None] = mapped_column(String(150))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_bn: Mapped[str | None] = mapped_column(Text)
    seo_description: Mapped[str | None] = mapped_column(String(170))


class Faq(_Publishable, TimestampMixin, Base):
    __tablename__ = "faqs"
    __table_args__ = (
        CheckConstraint(f"status IN {STATUSES}", name="status_valid"),
        Index("ix_faqs_category", "category", "sort_order"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUIDPk]
    category: Mapped[str] = mapped_column(String(40), nullable=False, server_default="general")
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    question_bn: Mapped[str | None] = mapped_column(String(300))
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    answer_bn: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
