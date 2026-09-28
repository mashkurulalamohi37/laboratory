"""Base abstract interface for payment gateway providers."""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PaymentInitResult:
    provider_txn_id: str
    redirect_url: str | None
    gateway_data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PaymentVerifyResult:
    provider_txn_id: str
    status: str  # "SUCCEEDED", "FAILED", "PENDING"
    amount: int
    raw_response: dict[str, Any]


class PaymentProvider(abc.ABC):
    @abc.abstractmethod
    async def initiate_payment(
        self,
        *,
        payment_id: uuid.UUID,
        booking_code: str,
        amount: int,  # poisha
        customer_name: str,
        customer_phone: str | None,
        callback_url: str,
    ) -> PaymentInitResult:
        """Initiate payment session with provider and return redirect URL or tokens."""

    @abc.abstractmethod
    async def verify_payment(self, provider_txn_id: str) -> PaymentVerifyResult:
        """Verify transaction with provider API."""
