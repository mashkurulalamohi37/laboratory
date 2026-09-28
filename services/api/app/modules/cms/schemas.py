"""CMS request/response schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.core.text import SLUG_PATTERN

Status = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
Placement = Literal["HOME_HERO", "HOME_STRIP"]
Tone = Literal["brand", "accent", "neutral"]

_SAFE_HREF = re.compile(r"^(/(?!/)[A-Za-z0-9\-._~/?#=&%]*|https://[^\s<>\"']+)$")


def _href(v: str | None) -> str | None:
    """Internal paths or https URLs only: no javascript:, data:, protocol-relative, etc."""
    if v is None or not v.strip():
        return None
    v = v.strip()
    if not _SAFE_HREF.match(v):
        raise ValueError("must be a site path starting with / or an https:// URL")
    return v


SafeHref = Annotated[str | None, AfterValidator(_href)]
Slug = Annotated[str, Field(min_length=2, max_length=120, pattern=SLUG_PATTERN)]


class _Window(BaseModel):
    status: Status = "DRAFT"
    publish_at: datetime | None = Field(
        default=None, description="Scheduled publication time; null = immediately"
    )


# ---------------------------------------------------------------- banners
class BannerIn(_Window):
    placement: Placement = "HOME_HERO"
    title: str = Field(min_length=2, max_length=120)
    title_bn: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=300)
    body_bn: str | None = Field(default=None, max_length=300)
    cta_label: str | None = Field(default=None, max_length=40)
    cta_label_bn: str | None = Field(default=None, max_length=40)
    cta_href: SafeHref = None
    tone: Tone = "brand"
    sort_order: int = Field(default=0, ge=0, le=10_000)
    unpublish_at: datetime | None = None

    @model_validator(mode="after")
    def _window(self) -> BannerIn:
        if self.unpublish_at and self.publish_at and self.unpublish_at <= self.publish_at:
            raise ValueError("unpublish_at must be after publish_at")
        if bool(self.cta_label) != bool(self.cta_href):
            raise ValueError("cta_label and cta_href go together")
        return self


class BannerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    placement: Placement
    title: str
    title_bn: str | None
    body: str | None
    body_bn: str | None
    cta_label: str | None
    cta_label_bn: str | None
    cta_href: str | None
    tone: Tone
    sort_order: int


class AdminBannerOut(BannerOut):
    status: Status
    publish_at: datetime | None
    unpublish_at: datetime | None
    version: int
    updated_at: datetime


# ---------------------------------------------------------------- pages
class PageIn(_Window):
    slug: Slug
    title: str = Field(min_length=2, max_length=150)
    title_bn: str | None = Field(default=None, max_length=150)
    body: str = Field(min_length=1, max_length=50_000, description="Markdown subset")
    body_bn: str | None = Field(default=None, max_length=50_000)
    seo_description: str | None = Field(default=None, max_length=170)


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    title_bn: str | None
    body: str
    body_bn: str | None
    seo_description: str | None
    updated_at: datetime


class AdminPageOut(PageOut):
    id: uuid.UUID
    status: Status
    publish_at: datetime | None
    version: int


# ---------------------------------------------------------------- FAQs
class FaqIn(_Window):
    category: str = Field(default="general", min_length=2, max_length=40, pattern=SLUG_PATTERN)
    question: str = Field(min_length=5, max_length=300)
    question_bn: str | None = Field(default=None, max_length=300)
    answer: str = Field(min_length=2, max_length=5000)
    answer_bn: str | None = Field(default=None, max_length=5000)
    sort_order: int = Field(default=0, ge=0, le=10_000)


class FaqOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    question: str
    question_bn: str | None
    answer: str
    answer_bn: str | None
    sort_order: int


class AdminFaqOut(FaqOut):
    status: Status
    publish_at: datetime | None
    version: int
    updated_at: datetime
