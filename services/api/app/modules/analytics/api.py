"""REST API routes for analytics dashboards, turnaround metrics, and patient health trends."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.analytics.schemas import (
    AnalyticsDashboardOut,
    DepartmentWorkloadItem,
    PatientHealthTimelineOut,
    TatMetricsOut,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> AnalyticsService:
    return AnalyticsService(session)


@router.get("/dashboard", response_model=Envelope[AnalyticsDashboardOut])
async def get_dashboard(
    _: Annotated[CurrentPrincipal, Depends(require(P.ANALYTICS_VIEW))],
    service: Annotated[AnalyticsService, Depends(get_service)],
) -> Envelope[AnalyticsDashboardOut]:
    """Get high-level operations, volume, and revenue dashboard metrics."""
    data = await service.get_dashboard()
    return ok(data)


@router.get("/departments", response_model=Envelope[list[DepartmentWorkloadItem]])
async def get_departments_workload(
    _: Annotated[CurrentPrincipal, Depends(require(P.ANALYTICS_VIEW))],
    service: Annotated[AnalyticsService, Depends(get_service)],
) -> Envelope[list[DepartmentWorkloadItem]]:
    """Get laboratory order volume and completion rate across clinical departments."""
    items = await service.get_department_workload()
    return ok(items)


@router.get("/tat", response_model=Envelope[TatMetricsOut])
async def get_tat_metrics(
    _: Annotated[CurrentPrincipal, Depends(require(P.ANALYTICS_VIEW))],
    service: Annotated[AnalyticsService, Depends(get_service)],
) -> Envelope[TatMetricsOut]:
    """Get turnaround time (TAT) benchmark metrics."""
    metrics = await service.get_tat_metrics()
    return ok(metrics)


@router.get("/patient/{patient_id}/timeline", response_model=Envelope[PatientHealthTimelineOut])
async def get_patient_timeline(
    patient_id: uuid.UUID,
    _: Annotated[CurrentPrincipal, Depends(require())],
    service: Annotated[AnalyticsService, Depends(get_service)],
) -> Envelope[PatientHealthTimelineOut]:
    """Retrieve longitudinal clinical analyte readings for a patient over time."""
    timeline = await service.get_patient_timeline(patient_id)
    return ok(timeline)
