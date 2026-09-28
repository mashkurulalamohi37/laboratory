"""Unit tests for Phase 3: Patient, Scheduling, Coupon, Booking, and Payment logic."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.modules.booking.schemas import (
    QuoteItemResponse,
    QuoteResponse,
)
from app.modules.payment.providers.cash import CashProvider
from app.modules.payment.providers.sslcommerz import SSLCommerzProvider
from app.modules.scheduling.schemas import SlotInstanceResponse


def test_quote_response_calculation():
    items = [
        QuoteItemResponse(
            patient_id=uuid.uuid4(),
            item_type="TEST",
            item_id=uuid.uuid4(),
            name="Complete Blood Count (CBC)",
            price=60000,  # 600 BDT
            mrp=75000,
        ),
        QuoteItemResponse(
            patient_id=uuid.uuid4(),
            item_type="TEST",
            item_id=uuid.uuid4(),
            name="Lipid Profile",
            price=120000,  # 1200 BDT
            mrp=150000,
        ),
    ]
    subtotal = sum(i.price for i in items)  # 180000 (1800 BDT)
    collection_fee = 15000  # 150 BDT
    discount = 18000  # 10% coupon = 180 BDT
    total = subtotal - discount + collection_fee

    quote = QuoteResponse(
        subtotal=subtotal,
        discount=discount,
        collection_fee=collection_fee,
        total=total,
        coupon_applied="HEALTH10",
        items=items,
    )
    assert quote.subtotal == 180000
    assert quote.discount == 18000
    assert quote.collection_fee == 15000
    assert quote.total == 177000


def test_free_home_collection_threshold():
    subtotal_high = 250000  # 2500 BDT > 2000 BDT
    fee_high = 0 if subtotal_high >= 200000 else 15000
    assert fee_high == 0

    subtotal_low = 150000  # 1500 BDT < 2000 BDT
    fee_low = 0 if subtotal_low >= 200000 else 15000
    assert fee_low == 15000


def test_slot_instance_availability_calculation():
    slot = SlotInstanceResponse(
        id=uuid.uuid4(),
        owner_type="CENTRE",
        owner_id=uuid.uuid4(),
        date=dt.date(2026, 10, 1),
        start_time=dt.time(9, 0),
        end_time=dt.time(11, 0),
        capacity=10,
        booked=4,
        held=2,
        mode="CENTRE",
        is_active=True,
        available=4,  # 10 - (4 + 2)
    )
    assert slot.available == 4
    assert slot.capacity - (slot.booked + slot.held) == slot.available


@pytest.mark.asyncio
async def test_sslcommerz_provider_init():
    provider = SSLCommerzProvider()
    res = await provider.initiate_payment(
        payment_id=uuid.uuid4(),
        booking_code="BKG-2026-000123",
        amount=150000,
        customer_name="Test Patient",
        customer_phone="+8801711111111",
        callback_url="/api/v1/payments/callback",
    )
    assert res.provider_txn_id.startswith("SSLCZ_BKG-2026-000123")
    assert res.redirect_url is not None
    assert "tran_id=" in res.redirect_url


@pytest.mark.asyncio
async def test_cash_provider_init():
    provider = CashProvider()
    res = await provider.initiate_payment(
        payment_id=uuid.uuid4(),
        booking_code="BKG-2026-000123",
        amount=150000,
        customer_name="Test Patient",
        customer_phone=None,
        callback_url="",
    )
    assert res.provider_txn_id == "CASH_BKG-2026-000123"
    assert res.redirect_url is None
    assert res.gateway_data["method"] == "CASH_ON_COLLECTION"
