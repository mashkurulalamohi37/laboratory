"""Integration tests for Phase 3: Patient, Scheduling, Coupon, Booking, and Payment flows."""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_patient_and_family_flow(client: AsyncClient, patient_token: str) -> None:
    headers = {"Authorization": f"Bearer {patient_token}"}

    # 1. Get self profile
    res = await client.get("/api/v1/patients/me", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["patient_code"].startswith("PT-")

    # 2. Add family member
    family_payload = {
        "full_name": "Rahima Begum",
        "full_name_bn": "রহিমা বেগম",
        "dob": "1965-05-12",
        "sex": "F",
        "relationship": "MOTHER",
        "blood_group": "B+",
    }
    res2 = await client.post("/api/v1/patients/family", json=family_payload, headers=headers)
    assert res2.status_code == 201
    f_data = res2.json()["data"]
    assert f_data["relationship"] == "MOTHER"
    assert f_data["patient"]["full_name"] == "Rahima Begum"

    # 3. List family members
    res3 = await client.get("/api/v1/patients/family", headers=headers)
    assert res3.status_code == 200
    assert len(res3.json()["data"]) >= 1


@pytest.mark.integration
async def test_address_management(client: AsyncClient, patient_token: str) -> None:
    headers = {"Authorization": f"Bearer {patient_token}"}

    # 1. Create address
    addr_payload = {
        "house": "House 12/A",
        "road": "Road 5, Dhanmondi",
        "block": "Block B",
        "landmark": "Near Ibn Sina Hospital",
        "label": "HOME",
        "is_default": True,
    }
    res = await client.post("/api/v1/addresses", json=addr_payload, headers=headers)
    assert res.status_code == 201
    addr_id = res.json()["data"]["id"]

    # 2. List addresses
    res2 = await client.get("/api/v1/addresses", headers=headers)
    assert res2.status_code == 200
    assert any(a["id"] == addr_id for a in res2.json()["data"])

    # 3. Delete address
    res3 = await client.delete(f"/api/v1/addresses/{addr_id}", headers=headers)
    assert res3.status_code == 200


@pytest.mark.integration
async def test_scheduling_and_slots(client: AsyncClient, patient_token: str) -> None:
    headers = {"Authorization": f"Bearer {patient_token}"}
    dummy_centre_id = str(uuid.uuid4())
    today = dt.date.today().isoformat()
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()

    # 1. Query available slots
    res = await client.get(
        f"/api/v1/slots/available?owner_type=CENTRE&owner_id={dummy_centre_id}&from_date={today}&to_date={tomorrow}&mode=CENTRE"
    )
    assert res.status_code == 200
    slots = res.json()["data"]
    assert len(slots) > 0
    slot_id = slots[0]["id"]

    # 2. Hold a slot
    hold_res = await client.post(
        "/api/v1/slots/hold",
        json={"slot_id": slot_id, "ttl_minutes": 10},
        headers=headers,
    )
    assert hold_res.status_code == 200
    assert "expires_at" in hold_res.json()["data"]


@pytest.mark.integration
async def test_booking_quote_and_creation(client: AsyncClient, patient_token: str) -> None:
    headers = {"Authorization": f"Bearer {patient_token}"}

    # First get self profile
    me_res = await client.get("/api/v1/patients/me", headers=headers)
    patient_id = me_res.json()["data"]["id"]
    dummy_test_id = str(uuid.uuid4())

    quote_req = {
        "mode": "HOME",
        "items": [{"patient_id": patient_id, "item_type": "TEST", "item_id": dummy_test_id}],
        "coupon_code": None,
    }
    quote_res = await client.post("/api/v1/bookings/quote", json=quote_req)
    assert quote_res.status_code == 200
    q_data = quote_res.json()["data"]
    assert q_data["subtotal"] > 0
    assert q_data["total"] > 0
