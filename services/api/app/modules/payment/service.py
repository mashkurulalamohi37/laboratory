"""Service for orchestrating payment flows, callbacks, and verification."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound
from app.core.outbox import emit
from app.modules.booking.repository import BookingRepository
from app.modules.payment.providers.base import PaymentProvider
from app.modules.payment.providers.cash import CashProvider
from app.modules.payment.providers.sslcommerz import SSLCommerzProvider
from app.modules.payment.repository import PaymentRepository
from app.modules.payment.schemas import (
    PaymentCallbackPayload,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyResponse,
)


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaymentRepository(session)
        self.booking_repo = BookingRepository(session)
        self.providers: dict[str, PaymentProvider] = {
            "SSLCOMMERZ": SSLCommerzProvider(),
            "CASH": CashProvider(),
        }

    async def initiate_payment(
        self,
        *,
        user_id: uuid.UUID,
        data: PaymentInitiateRequest,
    ) -> PaymentInitiateResponse:
        booking = await self.booking_repo.get_by_id(data.booking_id)
        if not booking:
            raise NotFound("Booking not found")

        provider_key = data.provider.upper()
        provider = self.providers.get(provider_key)
        if not provider:
            raise AppError(f"Unsupported payment provider: {data.provider}")

        # Create or update payment record
        payment = await self.repo.create_payment(
            booking_id=booking.id,
            method=data.method,
            provider=data.provider,
            amount=booking.total,
            status="INITIATED",
            idempotency_key=data.idempotency_key,
        )

        init_res = await provider.initiate_payment(
            payment_id=payment.id,
            booking_code=booking.booking_code,
            amount=booking.total,
            customer_name="Valued Patient",
            customer_phone=None,
            callback_url="/api/v1/payments/callback",
        )

        # Record transaction attempt
        await self.repo.add_transaction(
            payment_id=payment.id,
            provider_txn_id=init_res.provider_txn_id,
            amount=booking.total,
            status="INITIATED",
            raw_response=init_res.gateway_data,
        )

        if data.provider.upper() == "CASH":
            payment.status = "PENDING"
            await self.booking_repo.update_status(
                booking=booking,
                to_status="CONFIRMED",
                actor_user_id=user_id,
                reason="Booked with Cash on Collection",
            )

        return PaymentInitiateResponse(
            payment_id=payment.id,
            booking_id=booking.id,
            amount=booking.total,
            method=payment.method,
            provider=payment.provider,
            status=payment.status,
            provider_txn_id=init_res.provider_txn_id,
            redirect_url=init_res.redirect_url,
            gateway_data=init_res.gateway_data,
        )

    async def handle_callback(self, payload: PaymentCallbackPayload) -> dict[str, Any]:
        await self.repo.record_callback(
            provider=payload.provider,
            provider_txn_id=payload.provider_txn_id,
            event_type=payload.status,
            payload=payload.raw_payload or {"status": payload.status},
        )

        txn = await self.repo.get_by_txn_id(payload.provider_txn_id)
        if not txn:
            return {"status": "IGNORED", "message": "Transaction not found"}

        payment = txn.payment
        if payload.status.upper() in ("SUCCESS", "VALID", "SUCCEEDED"):
            txn.status = "SUCCEEDED"
            payment.status = "SUCCEEDED"

            # Advance booking status
            booking = await self.booking_repo.get_by_id(payment.booking_id)
            if booking and booking.status != "CONFIRMED":
                await self.booking_repo.update_status(
                    booking=booking,
                    to_status="CONFIRMED",
                    reason="Payment confirmed via gateway",
                )
                emit(
                    self.session,
                    topic="booking.confirmed",
                    payload={"booking_id": str(booking.id), "payment_id": str(payment.id)},
                )
        else:
            txn.status = "FAILED"
            payment.status = "FAILED"

        return {"status": "PROCESSED", "payment_status": payment.status}

    async def verify_payment(self, payment_id: uuid.UUID) -> PaymentVerifyResponse:
        payment = await self.repo.get_by_id(payment_id)
        if not payment:
            raise NotFound("Payment record not found")

        provider = self.providers.get(payment.provider.upper())
        latest_txn = payment.transactions[-1] if payment.transactions else None
        txn_id = latest_txn.provider_txn_id if latest_txn else f"TXN_{payment.id.hex[:8]}"

        if provider and latest_txn:
            verify_res = await provider.verify_payment(latest_txn.provider_txn_id)
            if verify_res.status == "SUCCEEDED" and payment.status != "SUCCEEDED":
                payment.status = "SUCCEEDED"
                booking = await self.booking_repo.get_by_id(payment.booking_id)
                if booking and booking.status != "CONFIRMED":
                    await self.booking_repo.update_status(
                        booking=booking,
                        to_status="CONFIRMED",
                        reason="Payment verified successfully",
                    )

        return PaymentVerifyResponse(
            payment_id=payment.id,
            booking_id=payment.booking_id,
            status=payment.status,
            amount=payment.amount,
            provider_txn_id=txn_id,
            verified_at=dt.datetime.now(dt.UTC),
        )
