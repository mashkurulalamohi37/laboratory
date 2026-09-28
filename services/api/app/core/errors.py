"""Standardised API errors.

Every error leaving the API has the shape::

    {"success": false, "error": {"code", "message", "details", "request_id"}}

Internal exception details are never exposed to clients.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import current_request_id
from app.core.logging import get_logger

log = get_logger(__name__)


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody


class AppError(Exception):
    """Base for all expected, client-facing errors."""

    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []
        self.headers = headers
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "Some fields are invalid."


class AuthRequired(AppError):
    status_code = 401
    code = "AUTH_REQUIRED"
    message = "Authentication is required."


class PermissionDenied(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


class VersionConflict(Conflict):
    code = "VERSION_CONFLICT"
    message = "This record was changed by someone else. Reload it and try again."


class BusinessRuleViolation(AppError):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"
    message = "The request violates a business rule."


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests. Please try again later."

    def __init__(self, retry_after: int, message: str | None = None) -> None:
        super().__init__(message, headers={"Retry-After": str(max(retry_after, 1))})


def _payload(code: str, message: str, details: list[ErrorDetail] | None = None) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(
            code=code, message=message, details=details or [], request_id=current_request_id()
        )
    ).model_dump()


_HTTP_CODE_MAP = {
    401: "AUTH_REQUIRED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            _payload(exc.code, exc.message, exc.details),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(
                field=".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "query")),
                issue=str(err.get("msg", "invalid")),
            )
            for err in exc.errors()
        ]
        return JSONResponse(
            _payload(ValidationFailed.code, ValidationFailed.message, details), status_code=400
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(_payload(code, message), status_code=exc.status_code)

    # Unexpected exceptions are converted to the INTERNAL_ERROR envelope by
    # RequestContextMiddleware, which still has the request ID bound at that point.


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses=` helper documenting the standard error envelope."""
    descriptions = {
        400: "Validation error",
        401: "Authentication required or failed",
        403: "Permission denied",
        404: "Not found",
        409: "Conflict / invalid state transition",
        422: "Business rule violation",
        429: "Rate limited",
    }
    return {c: {"model": ErrorResponse, "description": descriptions.get(c, "Error")} for c in codes}
