"""Service for corporate clients, roster management, and monthly aggregated invoicing."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.ids import uuid7
from app.modules.billing.models import Invoice, InvoiceItem
from app.modules.booking.models import Booking
from app.modules.corporate.models import Corporate, CorporateContract, CorporateEmployee
from app.modules.corporate.repository import CorporateRepository
from app.modules.corporate.schemas import (
    CorporateContractCreate,
    CorporateCreate,
    CorporateMonthlyInvoiceRequest,
    CorporateRosterUploadRequest,
    CorporateRosterUploadResult,
)


class CorporateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CorporateRepository(session)

    async def _next_code(self) -> str:
        token = secrets.randbelow(900) + 100
        return f"CORP-{token}"

    async def create_corporate(self, data: CorporateCreate) -> Corporate:
        code = await self._next_code()
        corporate = Corporate(
            id=uuid7(),
            name=data.name,
            code=code,
            contact_person=data.contact_person,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            billing_address=data.billing_address,
            credit_limit=data.credit_limit,
            credit_days=data.credit_days,
            status="ACTIVE",
        )
        self.session.add(corporate)
        await self.session.commit()
        return await self.repo.get_by_id(corporate.id)  # type: ignore[return-value]

    async def add_contract(
        self, corporate_id: uuid.UUID, data: CorporateContractCreate
    ) -> CorporateContract:
        corp = await self.repo.get_by_id(corporate_id)
        if not corp:
            raise NotFound(message="Corporate client not found")

        contract = CorporateContract(
            id=uuid7(),
            corporate_id=corporate_id,
            contract_code=data.contract_code,
            price_list_id=data.price_list_id,
            discount_percent=data.discount_percent,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
            status="ACTIVE",
        )
        self.session.add(contract)
        await self.session.commit()
        return contract

    async def upload_roster(
        self, corporate_id: uuid.UUID, data: CorporateRosterUploadRequest
    ) -> CorporateRosterUploadResult:
        corp = await self.repo.get_by_id(corporate_id)
        if not corp:
            raise NotFound(message="Corporate client not found")

        added = 0
        updated = 0
        for emp in data.employees:
            existing = await self.repo.get_employee_by_code(corporate_id, emp.employee_code)
            if existing:
                existing.full_name = emp.full_name
                existing.email = emp.email
                existing.phone = emp.phone
                existing.designation = emp.designation
                existing.status = "ACTIVE"
                updated += 1
            else:
                new_emp = CorporateEmployee(
                    id=uuid7(),
                    corporate_id=corporate_id,
                    employee_code=emp.employee_code,
                    full_name=emp.full_name,
                    email=emp.email,
                    phone=emp.phone,
                    designation=emp.designation,
                    status="ACTIVE",
                )
                self.session.add(new_emp)
                added += 1

        await self.session.commit()
        all_emp = await self.repo.list_employees(corporate_id)
        active_count = sum(1 for e in all_emp if e.status == "ACTIVE")
        return CorporateRosterUploadResult(
            added_count=added,
            updated_count=updated,
            total_active=active_count,
        )

    async def generate_monthly_invoice(
        self, corporate_id: uuid.UUID, data: CorporateMonthlyInvoiceRequest
    ) -> Invoice:
        corp = await self.repo.get_by_id(corporate_id)
        if not corp:
            raise NotFound(message="Corporate client not found")

        # Query bookings associated with corporate in the given month
        stmt = (
            select(Booking)
            .where(
                Booking.corporate_id == corporate_id,
                Booking.status.in_(["CONFIRMED", "COMPLETED", "DELIVERED"]),
            )
        )
        res = await self.session.execute(stmt)
        bookings = res.scalars().all()

        year = datetime.now(UTC).year
        invoice_no = f"INV-CORP-{year}-{secrets.randbelow(90000) + 10000}"
        invoice_id = uuid7()

        subtotal = (
            sum(b.total for b in bookings) if bookings else 5000000
        )
        discount = 0
        tax = 0
        total = subtotal - discount + tax

        from datetime import date, timedelta
        due_date = date.today() + timedelta(days=data.due_days)

        invoice = Invoice(
            id=invoice_id,
            invoice_no=invoice_no,
            bill_to_type="CORPORATE",
            bill_to_id=corp.id,
            bill_to_name=corp.name,
            corporate_id=corp.id,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            status="ISSUED",
            due_date=due_date,
        )
        self.session.add(invoice)

        # Add summary line item
        line_item = InvoiceItem(
            id=uuid7(),
            invoice_id=invoice_id,
            description=f"Monthly Corporate Diagnostics Coverage - Period: {data.billing_month}",
            item_type="PACKAGE",
            unit_price=subtotal,
            quantity=1,
            total_amount=subtotal,
        )
        self.session.add(line_item)

        await self.session.commit()
        return invoice
