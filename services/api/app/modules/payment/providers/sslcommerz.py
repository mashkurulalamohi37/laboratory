"""SSLCommerz sandbox payment adapter."""

from __future__ import annotations

import uuid

from app.modules.payment.providers.base import (
    PaymentInitResult,
    PaymentProvider,
    PaymentVerifyResult,
)


class SSLCommerzProvider(PaymentProvider):
    """SSLCommerz payment gateway adapter (Sandbox / Demo mode)."""

    def __init__(
        self,
        store_id: str = "nirnoy_sandbox",
        store_passwd: str = "sandbox_pass",  # noqa: S107
    ) -> None:
        self.store_id = store_id
        self.store_passwd = store_passwd

    async def initiate_payment(
        self,
        *,
        payment_id: uuid.UUID,
        booking_code: str,
        amount: int,  # in poisha
        customer_name: str,
        customer_phone: str | None,
        callback_url: str,
    ) -> PaymentInitResult:
        txn_id = f"SSLCZ_{booking_code}_{uuid.uuid4().hex[:8]}"
        amount_bdt = amount / 100
        val_id = uuid.uuid4().hex[:12]

        # In sandbox mode, return demo redirect link with gateway simulated payload
        redirect_url = (
            f"/api/v1/payments/sandbox-mock?tran_id={txn_id}&val_id={val_id}&amount={amount_bdt}"
        )

        gateway_data = {
            "store_id": self.store_id,
            "tran_id": txn_id,
            "total_amount": amount_bdt,
            "currency": "BDT",
            "cus_name": customer_name,
            "cus_phone": customer_phone or "+8801700000000",
            "status": "SUCCESS",
            "GatewayPageURL": redirect_url,
        }

        return PaymentInitResult(
            provider_txn_id=txn_id,
            redirect_url=redirect_url,
            gateway_data=gateway_data,
        )

    async def verify_payment(self, provider_txn_id: str) -> PaymentVerifyResult:
        # Validate sandbox transaction
        return PaymentVerifyResult(
            provider_txn_id=provider_txn_id,
            status="SUCCEEDED",
            amount=0,
            raw_response={"status": "VALIDATED", "tran_id": provider_txn_id},
        )
