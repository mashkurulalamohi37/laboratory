"""Pydantic schemas for executive analytics, department workloads, TAT, and patient health.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AnalyticsDashboardOut(BaseModel):
    total_bookings: int
    total_revenue: int  # Poisha
    pending_collections: int
    samples_in_lab: int
    results_verified: int
    reports_released: int
    critical_alerts_unack: int
    today_bookings: int
    today_revenue: int


class DepartmentWorkloadItem(BaseModel):
    department: str
    total_orders: int
    completed_orders: int


class TatMetricsOut(BaseModel):
    avg_booking_to_collection_hours: float
    avg_collection_to_verify_hours: float
    avg_overall_tat_hours: float
    total_samples_analyzed: int


class AnalyteReading(BaseModel):
    test_name: str
    parameter_name: str
    value: str
    numeric_value: float | None = None
    unit: str
    flag: str
    recorded_at: datetime


class PatientHealthTimelineOut(BaseModel):
    patient_id: uuid.UUID
    total_investigations: int
    readings: list[AnalyteReading]
