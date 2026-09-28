"""Unit tests for Phase 4 (Collection & Samples) and Phase 5 (Lab & Results)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.modules.catalog.ranges import Flag, RangeRule, evaluate
from app.modules.collection.models import AssignmentStatus
from app.modules.result.models import ResultFlag, ResultStatus
from app.modules.sample.models import SampleStatus


def test_collection_assignment_lifecycle_enum() -> None:
    assert AssignmentStatus.PENDING == "PENDING"
    assert AssignmentStatus.ASSIGNED == "ASSIGNED"
    assert AssignmentStatus.ACCEPTED == "ACCEPTED"
    assert AssignmentStatus.ON_THE_WAY == "ON_THE_WAY"
    assert AssignmentStatus.ARRIVED == "ARRIVED"
    assert AssignmentStatus.PATIENT_VERIFIED == "PATIENT_VERIFIED"
    assert AssignmentStatus.COLLECTED == "COLLECTED"
    assert AssignmentStatus.CANCELLED == "CANCELLED"


def test_sample_status_lifecycle_enum() -> None:
    assert SampleStatus.CREATED == "CREATED"
    assert SampleStatus.COLLECTED == "COLLECTED"
    assert SampleStatus.IN_TRANSIT == "IN_TRANSIT"
    assert SampleStatus.RECEIVED == "RECEIVED"
    assert SampleStatus.PROCESSING == "PROCESSING"
    assert SampleStatus.COMPLETED == "COMPLETED"
    assert SampleStatus.REJECTED == "REJECTED"


def test_result_flag_and_status_enum() -> None:
    assert ResultFlag.N == "N"
    assert ResultFlag.L == "L"
    assert ResultFlag.H == "H"
    assert ResultFlag.CL == "CL"
    assert ResultFlag.CH == "CH"
    assert ResultStatus.ENTERED == "ENTERED"
    assert ResultStatus.PENDING_VERIFICATION == "PENDING_VERIFICATION"
    assert ResultStatus.VERIFIED == "VERIFIED"
    assert ResultStatus.AMENDED == "AMENDED"


def test_reference_range_flagging_critical_and_normal() -> None:
    rule = RangeRule(
        id=uuid.uuid4(),
        sex="M",
        age_min_days=18 * 365,
        age_max_days=65 * 365,
        sample_type_id=None,
        lab_id=None,
        method=None,
        effective_from=date(2020, 1, 1),
        effective_to=None,
        low=Decimal("3.5"),
        high=Decimal("5.0"),
        critical_low=Decimal("2.8"),
        critical_high=Decimal("6.5"),
    )

    # Normal range
    assert evaluate(Decimal("4.2"), rule) == Flag.NORMAL
    # High
    assert evaluate(Decimal("5.5"), rule) == Flag.HIGH
    # Low
    assert evaluate(Decimal("3.2"), rule) == Flag.LOW
    # Critical High (e.g. K = 6.8 mmol/L)
    assert evaluate(Decimal("6.8"), rule) == Flag.CRITICAL_HIGH
    # Critical Low
    assert evaluate(Decimal("2.5"), rule) == Flag.CRITICAL_LOW
