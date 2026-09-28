"""Application factory for the Nirnoy Diagnostics API (modular monolith)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.db import dispose_engine
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.redis import close_redis
from app.modules.analytics.api import router as analytics_router
from app.modules.audit.api import router as audit_router
from app.modules.auth.admin_api import router as access_admin_router
from app.modules.auth.api import me_router
from app.modules.auth.api import router as auth_router
from app.modules.billing.api import router as billing_router
from app.modules.booking.api import admin_router as booking_admin_router
from app.modules.booking.api import router as booking_router
from app.modules.catalog.admin_api import router as catalog_admin_router
from app.modules.catalog.api import router as catalog_router
from app.modules.centre.api import admin_router as centre_admin_router
from app.modules.centre.api import router as centre_router
from app.modules.cms.api import admin_router as cms_admin_router
from app.modules.cms.api import router as cms_router
from app.modules.collection.api import admin_router as collection_admin_router
from app.modules.collection.api import router as collection_router
from app.modules.corporate.api import router as corporate_router
from app.modules.coupon.api import router as coupon_router
from app.modules.crm.api import router as crm_router
from app.modules.finance.api import router as finance_router
from app.modules.geo.api import router as geo_router
from app.modules.inventory.api import router as inventory_router
from app.modules.lab.api import router as lab_router
from app.modules.notification.api import router as notification_router
from app.modules.partner.api import router as partner_router
from app.modules.patient.api import router as patient_router
from app.modules.payment.api import router as payment_router
from app.modules.report.api import patient_router as patient_reports_router
from app.modules.report.api import public_verify_router as report_verify_router
from app.modules.report.api import router as report_router
from app.modules.result.api import router as result_router
from app.modules.sample.api import router as sample_router
from app.modules.scheduling.api import router as scheduling_router
from app.modules.search.api import router as search_router
from app.modules.system.api import router as system_router

API_DESCRIPTION = """
Diagnostic laboratory platform API.

**Envelope.** Successful responses: `{"success": true, "data": ..., "meta": {...}}`.
Errors: `{"success": false, "error": {"code", "message", "details", "request_id"}}`.

**Auth.** Send `Authorization: Bearer <access_token>`. Web clients refresh through the
HttpOnly `nirnoy_rt` cookie at `POST /api/v1/auth/refresh`.

**Authorisation.** Each endpoint states its required permission. Permissions are enforced
server-side and may be scoped (branch, lab, corporate, partner).
"""


def _init_sentry() -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        send_default_pii=False,
        traces_sample_rate=0.05,
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_logger(__name__).info("api_started", environment=get_settings().environment)
    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, service="api")
    _init_sentry()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=API_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "X-Request-ID",
            "Accept-Language",
        ],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)  # outermost: wraps CORS and errors

    app.include_router(system_router)
    for router in (
        auth_router,
        me_router,
        catalog_router,
        search_router,
        centre_router,
        geo_router,
        cms_router,
        patient_router,
        scheduling_router,
        coupon_router,
        booking_router,
        payment_router,
        collection_router,
        collection_admin_router,
        sample_router,
        lab_router,
        result_router,
        report_router,
        patient_reports_router,
        report_verify_router,
        billing_router,
        corporate_router,
        partner_router,
        inventory_router,
        finance_router,
        crm_router,
        notification_router,
        analytics_router,
        access_admin_router,
        catalog_admin_router,
        centre_admin_router,
        cms_admin_router,
        booking_admin_router,
        audit_router,
    ):
        app.include_router(router, prefix=settings.api_prefix)

    Instrumentator(excluded_handlers=["/health", "/live", "/ready", "/metrics"]).instrument(
        app
    ).expose(app, endpoint="/metrics", include_in_schema=False)
    return app


app = create_app()
