"""Liveness/readiness probes (unversioned, unauthenticated, not rate-limited)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.db import ping_database
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.storage import ping_storage

router = APIRouter(tags=["system"])
log = get_logger(__name__)


@router.get("/health", summary="Process is up")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    return {"status": "ok"}


async def _check(name: str, fn: Callable[[], Awaitable[object]]) -> tuple[str, bool]:
    try:
        await asyncio.wait_for(fn(), timeout=2.0)
        return name, True
    except Exception as exc:
        log.warning("readiness_check_failed", dependency=name, error=type(exc).__name__)
        return name, False


@router.get(
    "/ready",
    summary="Readiness probe",
    description="PostgreSQL and Redis are critical; storage is informational.",
)
async def ready() -> JSONResponse:
    results = dict(
        await asyncio.gather(
            _check("postgres", ping_database),
            _check("redis", get_redis().ping),
            _check("storage", ping_storage),
        )
    )
    # Storage is reported but not critical: most endpoints work without it.
    healthy = results["postgres"] and results["redis"]
    return JSONResponse(
        {
            "status": "ok" if healthy else "degraded",
            "checks": {k: "ok" if v else "fail" for k, v in results.items()},
        },
        status_code=200 if healthy else 503,
    )
