"""Business logic service for financial expenses, reconciliation, and AR/AP."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.ids import uuid7
from app.modules.billing.models import Invoice
from app.modules.booking.models import Booking
from app.modules.finance.models import ArApRecord, Expense
from app.modules.finance.repository import FinanceRepository
from app.modules.finance.schemas import (
    ArApRecordCreate,
    ExpenseCreate,
    FinancialReconciliationOut,
)


class FinanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FinanceRepository(session)

    async def create_expense(
        self, data: ExpenseCreate, actor_id: uuid.UUID
    ) -> Expense:
        year = datetime.now(UTC).year
        voucher_no = f"EXP-{year}-{secrets.randbelow(900000) + 100000}"

        expense = Expense(
            id=uuid7(),
            voucher_no=voucher_no,
            category=data.category,
            amount=data.amount,
            paid_to=data.paid_to,
            payment_method=data.payment_method,
            expense_date=data.expense_date,
            centre_id=data.centre_id,
            approved_by=actor_id,
            notes=data.notes,
        )
        self.session.add(expense)
        await self.session.commit()
        return expense

    async def create_ar_ap(self, data: ArApRecordCreate) -> ArApRecord:
        record = ArApRecord(
            id=uuid7(),
            record_type=data.record_type,
            party_name=data.party_name,
            reference_id=data.reference_id,
            amount=data.amount,
            due_date=data.due_date,
            status="PENDING",
            notes=data.notes,
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def settle_ar_ap(self, record_id: uuid.UUID) -> ArApRecord:
        stmt = select(ArApRecord).where(ArApRecord.id == record_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            raise NotFound(message="Record not found")

        record.status = "SETTLED"
        record.settled_at = datetime.now(UTC)
        await self.session.commit()
        return record

    async def get_reconciliation(
        self, target_date: date, centre_id: uuid.UUID | None = None
    ) -> FinancialReconciliationOut:
        # Expenses
        expenses = await self.repo.list_expenses(
            centre_id=centre_id, from_date=target_date, to_date=target_date
        )
        total_expenses = sum(e.amount for e in expenses)
        breakdown: dict[str, int] = {}
        for e in expenses:
            breakdown[e.category] = breakdown.get(e.category, 0) + e.amount

        # Paid Invoices
        inv_stmt = select(Invoice).where(
            Invoice.status == "PAID",
        )
        inv_res = await self.session.execute(inv_stmt)
        invoices = inv_res.scalars().all()
        total_invoice_rev = sum(i.total for i in invoices)

        # Paid Bookings
        book_stmt = select(Booking).where(
            Booking.status.in_(["CONFIRMED", "COMPLETED", "DELIVERED"]),
        )
        if centre_id:
            book_stmt = book_stmt.where(Booking.centre_id == centre_id)
        book_res = await self.session.execute(book_stmt)
        bookings = book_res.scalars().all()
        total_booking_rev = sum(b.total for b in bookings)

        total_revenue = total_invoice_rev + total_booking_rev
        net_balance = total_revenue - total_expenses

        # Pending AR/AP
        ar_stmt = select(ArApRecord).where(
            ArApRecord.record_type == "RECEIVABLE", ArApRecord.status == "PENDING"
        )
        ap_stmt = select(ArApRecord).where(
            ArApRecord.record_type == "PAYABLE", ArApRecord.status == "PENDING"
        )
        receivables = sum(r.amount for r in (await self.session.execute(ar_stmt)).scalars().all())
        payables = sum(p.amount for p in (await self.session.execute(ap_stmt)).scalars().all())

        return FinancialReconciliationOut(
            reconciliation_date=target_date,
            centre_id=centre_id,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_operating_balance=net_balance,
            expense_breakdown=breakdown,
            receivables_pending=receivables,
            payables_pending=payables,
        )
