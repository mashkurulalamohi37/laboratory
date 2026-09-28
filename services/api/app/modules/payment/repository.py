"""Database repository for payments, transactions, and callbacks."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.payment.models import Payment, PaymentCallback, PaymentTransaction


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        query = (
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.transactions))
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_booking_id(self, booking_id: uuid.UUID) -> Payment | None:
        query = (
            select(Payment)
            .where(Payment.booking_id == booking_id)
            .options(selectinload(Payment.transactions))
            .order_by(Payment.created_at.desc())
        )
        return (await self.session.execute(query)).scalars().first()

    async def get_by_txn_id(self, provider_txn_id: str) -> PaymentTransaction | None:
        query = (
            select(PaymentTransaction)
            .where(PaymentTransaction.provider_txn_id == provider_txn_id)
            .options(selectinload(PaymentTransaction.payment))
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_payment(
        self,
        *,
        booking_id: uuid.UUID,
        method: str,
        provider: str,
        amount: int,
        status: str = "INITIATED",
        idempotency_key: str | None = None,
    ) -> Payment:
        payment = Payment(
            booking_id=booking_id,
            method=method,
            provider=provider,
            amount=amount,
            status=status,
            idempotency_key=idempotency_key,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def add_transaction(
        self,
        *,
        payment_id: uuid.UUID,
        provider_txn_id: str,
        amount: int,
        status: str,
        raw_response: dict[str, Any] | None = None,
    ) -> PaymentTransaction:
        txn = PaymentTransaction(
            payment_id=payment_id,
            provider_txn_id=provider_txn_id,
            amount=amount,
            status=status,
            raw_response=raw_response,
        )
        self.session.add(txn)
        await self.session.flush()
        return txn

    async def record_callback(
        self,
        *,
        provider: str,
        provider_txn_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> PaymentCallback:
        callback = PaymentCallback(
            provider=provider,
            provider_txn_id=provider_txn_id,
            event_type=event_type,
            payload=payload,
            processed_at=dt.datetime.now(dt.UTC),
        )
        self.session.add(callback)
        await self.session.flush()
        return callback
