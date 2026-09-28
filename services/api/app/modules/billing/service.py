"""Service for invoice generation, totals computation, and payment settlement."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.ids import uuid7
from app.modules.billing.models import Invoice, InvoiceItem
from app.modules.billing.repository import BillingRepository
from app.modules.billing.schemas import InvoiceCreateRequest


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BillingRepository(session)

    async def _next_invoice_no(self) -> str:
        year = datetime.now(UTC).year
        token = secrets.randbelow(900000) + 100000
        return f"INV-{year}-{token}"

    async def create_invoice(self, data: InvoiceCreateRequest) -> Invoice:
        invoice_id = uuid7()
        invoice_no = await self._next_invoice_no()

        subtotal = sum(item.unit_price * item.quantity for item in data.items)
        total = max(0, subtotal - data.discount + data.tax)
        due_date = date.today() + timedelta(days=data.due_days)

        invoice = Invoice(
            id=invoice_id,
            invoice_no=invoice_no,
            bill_to_type=data.bill_to_type,
            bill_to_id=data.bill_to_id,
            bill_to_name=data.bill_to_name,
            booking_id=data.booking_id,
            corporate_id=data.corporate_id,
            partner_id=data.partner_id,
            subtotal=subtotal,
            discount=data.discount,
            tax=data.tax,
            total=total,
            status="ISSUED",
            due_date=due_date,
        )
        self.session.add(invoice)

        for item in data.items:
            line_total = item.unit_price * item.quantity
            line_item = InvoiceItem(
                id=uuid7(),
                invoice_id=invoice_id,
                description=item.description,
                item_type=item.item_type,
                item_id=item.item_id,
                unit_price=item.unit_price,
                quantity=item.quantity,
                total_amount=line_total,
            )
            self.session.add(line_item)

        await self.session.commit()
        return await self.repo.get_by_id(invoice_id)  # type: ignore[return-value]

    async def settle_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            raise NotFound(message="Invoice not found")

        invoice.status = "PAID"
        invoice.paid_at = datetime.now(UTC)
        await self.session.commit()
        return invoice
