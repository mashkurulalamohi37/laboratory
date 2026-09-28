"""Structured JSON logging with request correlation and secret redaction."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from app.core.context import get_request_context

# Keys whose values must never reach logs (matched case-insensitively, substring).
_REDACT_KEYS = (
    "password",
    "otp",
    "verification_code",
    "token",
    "secret",
    "authorization",
    "cookie",
    "card",
    "pin",
    "result_value",
)
_REDACTED = "[REDACTED]"


def _redact_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(marker in lowered for marker in _REDACT_KEYS):
        return _REDACTED
    if isinstance(value, Mapping):
        return {k: _redact_value(str(k), v) for k, v in value.items()}
    return value


def redact_processor(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict.keys()):
        if key in ("event", "level", "timestamp", "logger"):
            continue
        event_dict[key] = _redact_value(key, event_dict[key])
    return event_dict


def add_request_context(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    ctx = get_request_context()
    if ctx is not None:
        event_dict.setdefault("request_id", ctx.request_id)
    return event_dict


def configure_logging(level: str = "INFO", service: str = "api") -> None:
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_request_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_processor,
    ]
    structlog.configure(
        processors=[
            *shared,
            structlog.processors.dict_tracebacks,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)
    # Route stdlib loggers (uvicorn, sqlalchemy) through a plain handler at WARNING+.
    logging.basicConfig(level=logging.WARNING, stream=sys.stdout, format="%(message)s")
    logging.getLogger("uvicorn.access").disabled = True  # replaced by our access log


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
