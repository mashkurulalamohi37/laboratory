"""FastAPI router for payments and webhooks."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal
from app.modules.payment.schemas import (
    PaymentCallbackPayload,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyResponse,
)
from app.modules.payment.service import PaymentService

router = APIRouter(tags=["payment"])


def get_payment_service(session: Annotated[AsyncSession, Depends(get_session)]) -> PaymentService:
    return PaymentService(session)


@router.post(
    "/payments/initiate",
    response_model=Envelope[PaymentInitiateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def initiate_payment(
    body: PaymentInitiateRequest,
    principal: CurrentPrincipal,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[PaymentInitiateResponse]:
    if idempotency_key and not body.idempotency_key:
        body.idempotency_key = idempotency_key
    res = await service.initiate_payment(
        user_id=principal.user_id,
        data=body,
    )
    return ok(res)


@router.post("/payments/callback")
async def payment_callback(
    body: PaymentCallbackPayload,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> dict[str, str]:
    res = await service.handle_callback(body)
    return {"status": res.get("status", "OK")}


@router.get("/payments/{payment_id}/verify", response_model=Envelope[PaymentVerifyResponse])
async def verify_payment(
    payment_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> Envelope[PaymentVerifyResponse]:
    res = await service.verify_payment(payment_id)
    return ok(res)


@router.get("/payments/sandbox-mock", response_class=HTMLResponse)
async def sandbox_mock_page(
    tran_id: str = "DEMO",
    amount: str = "0",
) -> str:
    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head><title>SSLCommerz Sandbox Gateway</title></head>",
        '<body style="font-family: sans-serif; display: flex; justify-content: center; '
        'align-items: center; min-height: 80vh; background: #f4f6f8;">',
        '  <div style="background: white; padding: 32px; border-radius: 12px; '
        'box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 420px; width: 100%;">',
        '    <h2 style="color: #0070ba; margin-top: 0;">SSLCommerz Sandbox</h2>',
        f"    <p>Transaction Reference: <strong>{tran_id}</strong></p>",
        f"    <p>Total Payable: <strong>৳{amount} BDT</strong></p>",
        '    <form method="POST" action="/api/v1/payments/callback">',
        '      <input type="hidden" name="provider" value="SSLCOMMERZ" />',
        f'      <input type="hidden" name="provider_txn_id" value="{tran_id}" />',
        '      <input type="hidden" name="status" value="SUCCESS" />',
        '      <button type="submit" style="width: 100%; padding: 12px; background: #0070ba; '
        'color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">',
        "        Simulate Successful Payment",
        "      </button>",
        "    </form>",
        "  </div>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html_lines)
