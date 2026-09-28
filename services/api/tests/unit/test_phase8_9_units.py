"""Unit tests for Phase 8 (inventory, finance, crm, notification) and Phase 9 (analytics)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.ids import uuid7
from app.modules.analytics.service import AnalyticsService
from app.modules.crm.schemas import TicketCreate, TicketMessageCreate
from app.modules.crm.service import CrmService
from app.modules.finance.schemas import ExpenseCreate
from app.modules.finance.service import FinanceService
from app.modules.inventory.models import InventoryItem
from app.modules.inventory.schemas import (
    InventoryItemCreate,
    StockMovementCreate,
)
from app.modules.inventory.service import InventoryService
from app.modules.notification.schemas import NotificationTemplateCreate
from app.modules.notification.service import NotificationManagementService


@pytest.mark.asyncio
async def test_inventory_item_and_movement() -> None:
    session = AsyncMock()
    service = InventoryService(session)

    # Mock get_by_code returning None (no existing item)
    service.repo.get_by_code = AsyncMock(return_value=None)

    data = InventoryItemCreate(
        name="EDTA K3 Vacuum Tube 3ml",
        code="ITM-EDTA-3ML",
        category="TUBE",
        unit_of_measure="PIECE",
        reorder_level=100,
        cost_per_unit=1250,  # 12.50 BDT
    )
    item = await service.create_item(data)
    assert item.code == "ITM-EDTA-3ML"
    assert item.current_stock == 0
    assert item.reorder_level == 100

    # Stock Movement (Inflow)
    service.repo.get_by_id = AsyncMock(return_value=item)
    service.repo.get_batch_by_no = AsyncMock(return_value=None)

    mov_data = StockMovementCreate(
        item_id=item.id,
        batch_no="BATCH-2026-X1",
        expiry_date=date(2027, 12, 31),
        movement_type="IN",
        quantity=500,
        reason="Initial supplier shipment",
    )
    actor_id = uuid7()
    mov = await service.record_movement(mov_data, actor_id)

    assert mov.quantity == 500
    assert item.current_stock == 500


@pytest.mark.asyncio
async def test_inventory_low_stock_alerts() -> None:
    session = AsyncMock()
    service = InventoryService(session)

    low_item = InventoryItem(
        id=uuid7(),
        name="Urine Container 50ml",
        code="ITM-URN-50ML",
        category="CONSUMABLE",
        unit_of_measure="PIECE",
        current_stock=20,
        reorder_level=100,
        cost_per_unit=500,
    )
    service.repo.list_low_stock = AsyncMock(return_value=[low_item])

    alerts = await service.get_low_stock_alerts()
    assert len(alerts) == 1
    assert alerts[0].deficit == 80
    assert alerts[0].item_code == "ITM-URN-50ML"


@pytest.mark.asyncio
async def test_finance_expense_and_reconciliation() -> None:
    session = AsyncMock()
    service = FinanceService(session)

    exp_data = ExpenseCreate(
        category="LOGISTICS",
        amount=150000,  # 1,500.00 BDT
        paid_to="Dhaka Cold Chain Express",
        payment_method="CASH",
        expense_date=date.today(),
        notes="Reagent transport between branches",
    )
    actor_id = uuid7()
    expense = await service.create_expense(exp_data, actor_id)
    assert expense.voucher_no.startswith("EXP-")
    assert expense.amount == 150000

    # Mock reconciliation queries
    service.repo.list_expenses = AsyncMock(return_value=[expense])

    # Mock execute for invoices and bookings
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_res)

    recon = await service.get_reconciliation(date.today())
    assert recon.total_expenses == 150000
    assert recon.expense_breakdown.get("LOGISTICS") == 150000


@pytest.mark.asyncio
async def test_crm_ticket_sla_and_messaging() -> None:
    session = AsyncMock()
    service = CrmService(session)

    ticket_data = TicketCreate(
        patient_name="Farhana Akter",
        phone="+8801712345678",
        category="REPORT",
        priority="URGENT",
        subject="Report delayed for appointment",
        description="Need urgent CBC report for doctor consult at 4pm.",
    )
    user_id = uuid7()

    mock_ticket = MagicMock()
    mock_ticket.ticket_no = "TCK-2026-10294"
    mock_ticket.status = "OPEN"
    service.repo.get_by_id = AsyncMock(return_value=mock_ticket)

    ticket = await service.create_ticket(ticket_data, user_id)
    assert ticket.ticket_no.startswith("TCK-")

    # Add message
    msg_data = TicketMessageCreate(
        message="We have flagged your CBC order as STAT for immediate pathologist review."
    )
    msg = await service.add_message(
        ticket_id=uuid7(),
        data=msg_data,
        sender_id=uuid7(),
        sender_name="Dr. Lab Supervisor",
        is_staff=True,
    )
    assert msg.is_staff is True
    assert "STAT" in msg.message


@pytest.mark.asyncio
async def test_notification_template_and_analytics() -> None:
    session = AsyncMock()
    notif_service = NotificationManagementService(session)

    # Template
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=res_mock)

    tpl_data = NotificationTemplateCreate(
        code="REPORT_READY",
        channel="SMS",
        language="BN",
        title="রিপোর্ট প্রস্তুত",
        body_template="আপনার নির্ণয় ডায়াগনস্টিক রিপোর্ট প্রস্তুত। দেখুন: {url}",
    )
    tpl = await notif_service.create_template(tpl_data)
    assert tpl.code == "REPORT_READY"

    # Analytics Service
    analytics = AnalyticsService(session)
    tat = await analytics.get_tat_metrics()
    assert tat.avg_overall_tat_hours > 0
    assert tat.avg_booking_to_collection_hours == 2.4
