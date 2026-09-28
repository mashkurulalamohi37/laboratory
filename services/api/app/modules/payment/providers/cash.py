"""Cash-on-collection payment provider."""

from __future__ import annotations

import uuid

from app.modules.payment.providers.base import (
    PaymentInitResult,
    PaymentProvider,
    PaymentVerifyResult,
)


class CashProvider(PaymentProvider):
    """Cash on collection (sample collector receives cash at home or front-desk)."""

    async def initiate_payment(
        self,
        *,
        payment_id: uuid.UUID,
        booking_code: str,
        amount: int,
        customer_name: str,
        customer_phone: str | None,
        callback_url: str,
    ) -> PaymentInitResult:
        txn_id = f"CASH_{booking_code}"
        return PaymentInitResult(
            provider_txn_id=txn_id,
            redirect_url=None,
            gateway_data={"method": "CASH_ON_COLLECTION", "amount": amount},
        )

    async def verify_payment(self, provider_txn_id: str) -> PaymentVerifyResult:
        return PaymentVerifyResult(
            provider_txn_id=provider_txn_id,
            status="PENDING",
            amount=0,
            raw_response={"status": "CASH_PENDING", "tran_id": provider_txn_id},
        )
