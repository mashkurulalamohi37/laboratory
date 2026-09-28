"""HTTP-level helpers shared by routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Response

from app.core.errors import ErrorDetail, ValidationFailed


def _if_match(
    if_match: Annotated[
        str | None,
        Header(
            alias="If-Match",
            description="Record `version` the edit is based on; a mismatch returns "
            "409 VERSION_CONFLICT. Optional.",
        ),
    ] = None,
) -> int | None:
    if if_match is None or not if_match.strip():
        return None
    raw = if_match.strip().removeprefix("W/").strip('"')
    if not raw.isdigit():
        raise ValidationFailed(details=[ErrorDetail(field="If-Match", issue="must be a version")])
    return int(raw)


#: Optimistic-lock version from the `If-Match` header (None when absent).
IfMatch = Annotated[int | None, Depends(_if_match)]


def public_cache(response: Response, seconds: int = 60) -> None:
    """Allow shared caches for anonymous catalog reads; stale copies may be served briefly
    while a fresh one is fetched."""
    response.headers["Cache-Control"] = (
        f"public, max-age={seconds}, stale-while-revalidate={seconds * 5}"
    )
