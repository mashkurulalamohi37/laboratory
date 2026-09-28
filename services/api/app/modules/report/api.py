"""API routes for clinical diagnostic reports, verification, and patient downloads."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.report.schemas import (
    ReportAmendRequest,
    ReportDownloadOut,
    ReportGenerateRequest,
    ReportOut,
    ReportShareCreate,
    ReportShareOut,
    ReportVerifyResponse,
)
from app.modules.report.service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])
patient_router = APIRouter(prefix="/patient/reports", tags=["Patient Reports"])
public_verify_router = APIRouter(prefix="/verify/reports", tags=["Public Report Verification"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ReportService:
    return ReportService(session)


# Staff & Lab Operations
@router.post("/generate", response_model=Envelope[ReportOut])
async def generate_report(
    data: ReportGenerateRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.REPORT_GENERATE))],
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[ReportOut]:
    """Generate final signed clinical report with cryptographic SHA-256 and QR token."""
    item = await service.generate_report(data, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


@router.get("/orders/{lab_order_id}", response_model=Envelope[ReportOut | None])
async def get_report_by_order(
    lab_order_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.REPORT_VIEW))],
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[ReportOut | None]:
    item = await service.repo.get_by_lab_order(lab_order_id)
    return ok(item)  # type: ignore[arg-type]


@router.post("/{report_id}/amend", response_model=Envelope[ReportOut])
async def amend_report(
    report_id: uuid.UUID,
    data: ReportAmendRequest,
    principal: Annotated[CurrentPrincipal, Depends(require(P.REPORT_AMEND))],
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[ReportOut]:
    """Amend an existing report, issuing version n+1 while superseding older versions."""
    item = await service.amend_report(report_id, data, actor_id=principal.user_id)
    return ok(item)  # type: ignore[arg-type]


# Patient Portal Endpoints
@patient_router.get("", response_model=Envelope[list[ReportOut]])
async def list_my_reports(
    principal: Annotated[CurrentPrincipal, Depends(require(P.PATIENT_VIEW))],
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[list[ReportOut]]:
    """List authenticated patient's reports."""
    items = await service.repo.list_by_patient(principal.user_id)
    return ok(list(items))  # type: ignore[arg-type]


@patient_router.get("/{report_id}/download", response_model=Envelope[ReportDownloadOut])
async def get_download_url(
    report_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require(P.REPORT_DOWNLOAD))],
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[ReportDownloadOut]:
    """Get secure, time-limited presigned download link for report PDF."""
    item = await service.get_download_url(report_id)
    return ok(item)


@patient_router.post("/{report_id}/share", response_model=Envelope[ReportShareOut])
async def create_share_link(
    report_id: uuid.UUID,
    data: ReportShareCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.PATIENT_VIEW))],
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[ReportShareOut]:
    """Generate time-limited public share link for doctor or caregiver access."""
    item = await service.create_share_link(report_id, data.expires_in_days)
    return ok(item)


# Public Verification
@public_verify_router.get("/{token}", response_model=Envelope[ReportVerifyResponse])
async def verify_report(
    token: str,
    service: Annotated[ReportService, Depends(get_service)],
) -> Envelope[ReportVerifyResponse]:
    """Publicly verify authenticity of a report via QR token without exposing full PHI."""
    item = await service.verify_report_token(token)
    return ok(item)
