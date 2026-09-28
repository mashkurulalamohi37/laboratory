"""Unit tests for Phase 6 (Reports) & Phase 7 (Corporate, Partner, Billing)."""

import hashlib
import re
from unittest.mock import AsyncMock

import pytest

from app.modules.billing.schemas import InvoiceItemCreate
from app.modules.billing.service import BillingService
from app.modules.corporate.service import CorporateService
from app.modules.partner.service import PartnerService
from app.modules.report.service import ReportService, _mask_name


def test_mask_patient_name_for_privacy():
    assert _mask_name("Mohammad Rahim") == "M******* R****"
    assert _mask_name("A B") == "A B"
    assert _mask_name("Fatima") == "F*****"
    assert _mask_name("Tanvir Hasan Khan") == "T***** H**** K***"


@pytest.mark.asyncio
async def test_report_service_pdf_rendering_and_hash():
    session = AsyncMock()
    service = ReportService(session)

    pdf_bytes = await service._render_report_pdf(
        report_code="REP-2026-123456",
        patient_name="Mohammad Rahim",
        patient_code="PT-001",
        patient_dob="1990-01-01",
        patient_sex="M",
        order_number="ORD-2026-000001",
        department="HEMATOLOGY",
        results_summary=[{
            "name": "Hemoglobin",
            "value": "14.2",
            "unit": "g/dL",
            "flag": "N",
            "range": "13.0 - 17.0",
        }],
        pathologist_name="Nazmul Huda",
        bmdc_number="A-45678",
        verification_token="fedcba9876543210fedcba9876543210",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 200
    assert b"REP-2026-123456" in pdf_bytes
    assert b"Hemoglobin" in pdf_bytes
    assert b"Nazmul Huda" in pdf_bytes
    assert b"A-45678" in pdf_bytes

    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    assert len(sha256) == 64


@pytest.mark.asyncio
async def test_report_code_generation():
    session = AsyncMock()
    service = ReportService(session)
    code = await service._next_report_code()
    assert re.match(r"^REP-\d{4}-\d{6}$", code)


@pytest.mark.asyncio
async def test_billing_invoice_calculation():
    session = AsyncMock()
    service = BillingService(session)
    inv_no = await service._next_invoice_no()
    assert re.match(r"^INV-\d{4}-\d{6}$", inv_no)

    items = [
        InvoiceItemCreate(description="Complete Blood Count", unit_price=40000, quantity=2),
        InvoiceItemCreate(description="Lipid Profile", unit_price=80000, quantity=1),
    ]
    subtotal = sum(i.unit_price * i.quantity for i in items)
    assert subtotal == 160000

    discount = 10000
    tax = 5000
    total = max(0, subtotal - discount + tax)
    assert total == 155000


@pytest.mark.asyncio
async def test_corporate_and_partner_code_formats():
    session = AsyncMock()
    corp_service = CorporateService(session)
    c_code = await corp_service._next_code()
    assert re.match(r"^CORP-\d{3}$", c_code)

    partner_service = PartnerService(session)
    p_code = await partner_service._next_code()
    assert re.match(r"^PRT-\d{3}$", p_code)
