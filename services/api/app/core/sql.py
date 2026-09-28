"""Small SQL helpers shared by module repositories."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, func, literal_column
from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, Conflict, ErrorDetail, ValidationFailed, VersionConflict

UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"
CHECK_VIOLATION = "23514"
EXCLUSION_VIOLATION = "23P01"


def _pg_error(exc: IntegrityError) -> tuple[str | None, str | None]:
    """(SQLSTATE, constraint name) from an IntegrityError raised through asyncpg."""
    orig = exc.orig
    cause = getattr(orig, "__cause__", None)
    code = getattr(orig, "pgcode", None) or getattr(cause, "sqlstate", None)
    constraint = getattr(cause, "constraint_name", None)
    return code, constraint


def integrity_to_app_error(
    exc: IntegrityError,
    *,
    duplicate: str = "A record with the same unique value already exists.",
    overlap_code: str = "OVERLAP",
    overlap: str = "This overlaps an existing record.",
) -> AppError:
    """Translate a constraint violation into a stable, client-facing error. The field is
    inferred from the constraint name (`uq_<table>_<column>` → `<column>`)."""
    code, constraint = _pg_error(exc)
    field = constraint.rsplit("_", 1)[-1] if constraint else None
    if code == UNIQUE_VIOLATION:
        details = [ErrorDetail(field=field, issue="already in use")] if field else []
        return Conflict(duplicate, code="DUPLICATE", details=details)
    if code == EXCLUSION_VIOLATION:
        return Conflict(overlap, code=overlap_code)
    if code == FOREIGN_KEY_VIOLATION:
        return ValidationFailed(
            "A referenced record does not exist.",
            details=[ErrorDetail(field=None, issue=constraint or "unknown reference")],
        )
    if code == CHECK_VIOLATION:
        return ValidationFailed(details=[ErrorDetail(field=None, issue=constraint or "invalid")])
    return Conflict()


def escape_like(value: str) -> str:
    """Treat user input literally inside LIKE patterns (escape char: backslash)."""
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def check_version(current: int, expected: int | None) -> None:
    """Optimistic locking: `expected` comes from the client's `If-Match` header (optional)."""
    if expected is not None and expected != current:
        raise VersionConflict()


def nfc(column: Any) -> ColumnElement[str]:
    """Unicode-normalise a nullable text column (NFC) so Bangla typed with precomposed or
    decomposed characters compares equal to normalised search input."""
    return func.normalize(func.coalesce(column, ""), literal_column("NFC"))
