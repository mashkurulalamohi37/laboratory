"""Pydantic schemas for reports, versions, signatures, verification, and sharing."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportSignatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pathologist_id: uuid.UUID
    pathologist_name: str
    bmdc_number: str
    designation: str | None = None
    signed_at: datetime
    signature_hash: str


class ReportVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    version_no: int
    storage_key: str
    sha256: str
    status: str
    amend_reason: str | None = None
    generated_at: datetime
    signatures: list[ReportSignatureOut] = Field(default_factory=list)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_code: str
    lab_order_id: uuid.UUID
    patient_id: uuid.UUID
    booking_id: uuid.UUID | None = None
    current_version_id: uuid.UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    versions: list[ReportVersionOut] = Field(default_factory=list)


class ReportGenerateRequest(BaseModel):
    lab_order_id: uuid.UUID
    pathologist_id: uuid.UUID
    pathologist_name: str
    bmdc_number: str
    designation: str | None = "Consultant Pathologist"


class ReportAmendRequest(BaseModel):
    amend_reason: str
    pathologist_id: uuid.UUID
    pathologist_name: str
    bmdc_number: str
    designation: str | None = "Consultant Pathologist"


class ReportDownloadOut(BaseModel):
    report_id: uuid.UUID
    version_no: int
    download_url: str
    expires_in_seconds: int = 300
    sha256: str


class ReportShareCreate(BaseModel):
    expires_in_days: int = Field(default=7, ge=1, le=90)


class ReportShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    share_url: str
    expires_at: datetime
    access_count: int


class ReportVerifyResponse(BaseModel):
    """Public verification response; validates authenticity without revealing full PHI."""

    is_valid: bool
    report_code: str
    version_no: int
    patient_masked_name: str  # e.g. "R***** K****"
    tests_included: list[str]
    generated_at: datetime
    verified_by_pathologist: str
    bmdc_number: str
    sha256: str
