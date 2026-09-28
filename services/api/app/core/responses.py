"""Success envelope used by every endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.context import current_request_id


class Meta(BaseModel):
    request_id: str | None = None
    page: int | None = None
    page_size: int | None = None
    total: int | None = None


class Envelope[T](BaseModel):
    success: bool = True
    data: T
    meta: Meta = Field(default_factory=Meta)


def ok[T](
    data: T, *, page: int | None = None, page_size: int | None = None, total: int | None = None
) -> Envelope[T]:
    return Envelope(
        data=data,
        meta=Meta(request_id=current_request_id(), page=page, page_size=page_size, total=total),
    )


class Page[T](BaseModel):
    items: list[T]
