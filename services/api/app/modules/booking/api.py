"""FastAPI router for patient quotes and bookings."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, OptionalPrincipal, require
from app.modules.auth.permissions import P
from app.modules.booking.schemas import (
    BookingCancelRequest,
    BookingCreate,
    BookingResponse,
    BookingStatusUpdate,
    QuoteRequest,
    QuoteResponse,
)
from app.modules.booking.service import BookingService

router = APIRouter(tags=["booking"])
admin_router = APIRouter(tags=["booking-admin"])


def get_booking_service(session: Annotated[AsyncSession, Depends(get_session)]) -> BookingService:
    return BookingService(session)


@router.post("/bookings/quote", response_model=Envelope[QuoteResponse])
async def calculate_quote(
    body: QuoteRequest,
    principal: OptionalPrincipal,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> Envelope[QuoteResponse]:
    user_id = principal.user_id if principal else None
    res = await service.calculate_quote(body, user_id=user_id)
    return ok(res)


@router.post(
    "/bookings",
    response_model=Envelope[BookingResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    body: BookingCreate,
    principal: CurrentPrincipal,
    service: Annotated[BookingService, Depends(get_booking_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[BookingResponse]:
    if idempotency_key and not body.idempotency_key:
        body.idempotency_key = idempotency_key
    res = await service.create_booking(
        user_id=principal.user_id,
        data=body,
        source="WEB",
    )
    return ok(res)


@router.get("/bookings/me", response_model=Envelope[list[BookingResponse]])
async def list_my_bookings(
    principal: CurrentPrincipal,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> Envelope[list[BookingResponse]]:
    bookings = await service.list_user_bookings(principal.user_id)
    return ok(bookings)


@router.get("/bookings/{booking_id}", response_model=Envelope[BookingResponse])
async def get_booking(
    booking_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> Envelope[BookingResponse]:
    res = await service.get_booking(booking_id, user_id=principal.user_id)
    return ok(res)


@router.post("/bookings/{booking_id}/cancel", response_model=Envelope[BookingResponse])
async def cancel_booking(
    booking_id: uuid.UUID,
    body: BookingCancelRequest,
    principal: CurrentPrincipal,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> Envelope[BookingResponse]:
    res = await service.cancel_booking(
        booking_id=booking_id,
        user_id=principal.user_id,
        reason=body.reason,
    )
    return ok(res)


# Admin routes
@admin_router.get("/admin/bookings", response_model=Envelope[list[BookingResponse]])
async def list_all_bookings_admin(
    principal: Annotated[CurrentPrincipal, Depends(require(P.BOOKING_VIEW))],
    service: Annotated[BookingService, Depends(get_booking_service)],
    status: Annotated[str | None, Query()] = None,
    mode: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Envelope[list[BookingResponse]]:
    offset = (page - 1) * page_size
    items, total = await service.list_all_bookings(
        status=status,
        mode=mode,
        limit=page_size,
        offset=offset,
    )
    return ok(items, page=page, page_size=page_size, total=total)


@admin_router.patch("/admin/bookings/{booking_id}/status", response_model=Envelope[BookingResponse])
async def update_booking_status_admin(
    booking_id: uuid.UUID,
    body: BookingStatusUpdate,
    principal: Annotated[CurrentPrincipal, Depends(require(P.BOOKING_UPDATE))],
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> Envelope[BookingResponse]:
    res = await service.update_status_admin(
        booking_id=booking_id,
        to_status=body.status,
        actor_user_id=principal.user_id,
        reason=body.reason,
    )
    return ok(res)
