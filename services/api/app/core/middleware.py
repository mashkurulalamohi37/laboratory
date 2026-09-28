"""Pure-ASGI middleware: request IDs, request context, access logging, security headers."""

from __future__ import annotations

import json
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import RequestContext, reset_request_context, set_request_context
from app.core.logging import get_logger

log = get_logger("access")

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_SKIP_ACCESS_LOG = {"/health", "/live", "/ready", "/metrics"}

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
    "cross-origin-opener-policy": "same-origin",
    "cache-control": "no-store",
}


class RequestContextMiddleware:
    """Assigns/propagates `X-Request-ID`, binds request context and writes the access log."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get("x-request-id", "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        client = scope.get("client")
        ctx = RequestContext(
            request_id=request_id,
            ip=client[0] if client else None,
            user_agent=(headers.get("user-agent") or "")[:512] or None,
        )
        token = set_request_context(ctx)
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                out = MutableHeaders(scope=message)
                out["x-request-id"] = request_id
                for name, value in SECURITY_HEADERS.items():
                    out.setdefault(name, value)
            await send(message)

        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send_wrapper(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            # Handled here, while the request context is still bound, so the log line and
            # the response both carry the request ID. Internals are never exposed.
            log.exception("unhandled_exception")
            if response_started:
                raise
            body = json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred.",
                        "details": [],
                        "request_id": request_id,
                    },
                }
            ).encode()
            await send_wrapper(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send_wrapper({"type": "http.response.body", "body": body})
        finally:
            path = scope.get("path", "")
            if path not in _SKIP_ACCESS_LOG:
                route = scope.get("route")
                log.info(
                    "http_request",
                    method=scope.get("method"),
                    endpoint=getattr(route, "path", path),
                    status=status_code,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    user_id=scope.get("state", {}).get("user_id"),
                )
            reset_request_context(token)
