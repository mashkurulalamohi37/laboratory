"""Per-request context shared by logging, auditing and error handling."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    ip: str | None = None
    user_agent: str | None = None


_request_ctx: ContextVar[RequestContext | None] = ContextVar("request_ctx", default=None)


def set_request_context(ctx: RequestContext) -> object:
    return _request_ctx.set(ctx)


def reset_request_context(token: object) -> None:
    _request_ctx.reset(token)  # type: ignore[arg-type]


def get_request_context() -> RequestContext | None:
    return _request_ctx.get()


def current_request_id() -> str | None:
    ctx = _request_ctx.get()
    return ctx.request_id if ctx else None
