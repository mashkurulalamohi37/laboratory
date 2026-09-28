"""Pydantic schemas for the result module."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResultParameterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    result_id: uuid.UUID
    parameter_id: uuid.UUID
    value_numeric: float | None = None
    value_text: str | None = None
    value_option: str | None = None
    unit_snapshot: str | None = None
    ref_range_snapshot: dict[str, Any] | None = None
    flag: str
    is_critical: bool
    delta_check_alert: bool


class ResultCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    result_id: uuid.UUID
    author_id: uuid.UUID
    comment_type: str
    comment_text: str
    created_at: datetime


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lab_order_item_id: uuid.UUID
    status: str
    version: int
    is_current: bool
    entered_by: uuid.UUID | None = None
    entered_at: datetime | None = None
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    amended_by: uuid.UUID | None = None
    amended_at: datetime | None = None
    amend_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    parameters: list[ResultParameterOut] = Field(default_factory=list)
    comments: list[ResultCommentOut] = Field(default_factory=list)


class ParameterEntry(BaseModel):
    parameter_id: uuid.UUID
    value_numeric: float | None = None
    value_text: str | None = None
    value_option: str | None = None


class ResultEnterRequest(BaseModel):
    lab_order_item_id: uuid.UUID
    patient_sex: str | None = None  # M, F, OTHER
    patient_dob_days: int | None = None  # age in days for exact range match
    parameters: list[ParameterEntry]
    comments: list[str] = Field(default_factory=list)


class ResultVerifyRequest(BaseModel):
    comments: str | None = None


class ResultReturnRequest(BaseModel):
    reason: str


class ResultAmendRequest(BaseModel):
    reason: str
    parameters: list[ParameterEntry]
    comments: list[str] = Field(default_factory=list)


class CriticalAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    result_parameter_id: uuid.UUID
    lab_order_item_id: uuid.UUID
    alert_type: str
    message: str
    status: str
    notified_users: list[dict[str, Any]] | None = None
    acknowledged_by: uuid.UUID | None = None
    acknowledged_at: datetime | None = None
    action_taken: str | None = None
    created_at: datetime


class AlertAcknowledgeRequest(BaseModel):
    action_taken: str | None = None
