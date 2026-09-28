"""Service for booking creation, quoting, and lifecycle state transitions."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound, PermissionDenied
from app.core.outbox import emit
from app.modules.booking.models import Booking
from app.modules.booking.repository import BookingRepository
from app.modules.booking.schemas import (
    BookingCreate,
    BookingItemResponse,
    BookingResponse,
    BookingStatusHistoryResponse,
    QuoteItemResponse,
    QuoteRequest,
    QuoteResponse,
)
from app.modules.catalog.models import Package, Test
from app.modules.catalog.repository import PriceScope
from app.modules.coupon.service import CouponService
from app.modules.scheduling.repository import SchedulingRepository

HOME_COLLECTION_FEE_POISHA = 15000  # ৳150
FREE_COLLECTION_THRESHOLD_POISHA = 200000  # ৳2,000


class BookingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BookingRepository(session)
        self.scheduling_repo = SchedulingRepository(session)
        self.coupon_service = CouponService(session)

    async def calculate_quote(
        self,
        data: QuoteRequest,
        user_id: uuid.UUID | None = None,
    ) -> QuoteResponse:
        price_scope = await PriceScope.load(self.session)

        # Collect IDs by type
        test_ids = [item.item_id for item in data.items if item.item_type == "TEST"]
        package_ids = [item.item_id for item in data.items if item.item_type == "PACKAGE"]

        # Load names and prices
        test_prices = await price_scope.prices(self.session, "TEST", test_ids)
        package_prices = await price_scope.prices(self.session, "PACKAGE", package_ids)

        # Query names
        test_names: dict[uuid.UUID, str] = {}
        if test_ids:
            t_rows = (
                await self.session.execute(select(Test.id, Test.name).where(Test.id.in_(test_ids)))
            ).all()
            test_names = {row[0]: row[1] for row in t_rows}

        pkg_names: dict[uuid.UUID, str] = {}
        if package_ids:
            p_rows = (
                await self.session.execute(
                    select(Package.id, Package.name).where(Package.id.in_(package_ids))
                )
            ).all()
            pkg_names = {row[0]: row[1] for row in p_rows}

        quote_items: list[QuoteItemResponse] = []
        subtotal = 0

        for item in data.items:
            if item.item_type == "TEST":
                name = test_names.get(item.item_id, "Diagnostic Test")
                p = test_prices.get(item.item_id)
                price = p.amount if p else 50000  # fallback 500 BDT
                mrp = p.mrp if p and p.mrp else price
            else:
                name = pkg_names.get(item.item_id, "Health Package")
                p = package_prices.get(item.item_id)
                price = p.amount if p else 150000  # fallback 1500 BDT
                mrp = p.mrp if p and p.mrp else price

            subtotal += price
            quote_items.append(
                QuoteItemResponse(
                    patient_id=item.patient_id,
                    item_type=item.item_type,
                    item_id=item.item_id,
                    name=name,
                    price=price,
                    mrp=mrp,
                )
            )

        # Collection fee calculation
        collection_fee = 0
        if data.mode == "HOME":
            collection_fee = (
                0 if subtotal >= FREE_COLLECTION_THRESHOLD_POISHA else HOME_COLLECTION_FEE_POISHA
            )

        # Coupon calculation
        discount = 0
        coupon_applied: str | None = None
        if data.coupon_code:
            coupon_res = await self.coupon_service.validate_and_calculate(
                code=data.coupon_code,
                user_id=user_id,
                subtotal=subtotal,
            )
            if coupon_res.valid:
                discount = coupon_res.discount_amount
                coupon_applied = coupon_res.code

        total = max(0, subtotal - discount + collection_fee)

        return QuoteResponse(
            subtotal=subtotal,
            discount=discount,
            collection_fee=collection_fee,
            total=total,
            coupon_applied=coupon_applied,
            items=quote_items,
        )

    async def create_booking(
        self,
        *,
        user_id: uuid.UUID,
        data: BookingCreate,
        source: str = "WEB",
    ) -> BookingResponse:
        # Idempotency check
        if data.idempotency_key:
            existing = await self.repo.get_by_idempotency_key(data.idempotency_key)
            if existing:
                return self._to_response(existing)

        # Check and lock slot
        slot = await self.scheduling_repo.get_slot_for_update(data.slot_id)
        if not slot:
            raise NotFound("Selected time slot does not exist")

        available_capacity = slot.capacity - slot.booked
        if available_capacity <= 0 and slot.held <= 0:
            raise Conflict("Selected slot is full. Please choose another time slot.")

        # Convert slot hold or book directly
        if slot.held > 0:
            slot.held -= 1
        slot.booked += 1

        # Calculate authoritative prices
        quote_req = QuoteRequest(
            mode=data.mode,
            centre_id=data.centre_id,
            address_id=data.address_id,
            items=data.items,
            coupon_code=data.coupon_code,
        )
        quote = await self.calculate_quote(quote_req, user_id=user_id)

        # Validate coupon ID if coupon code was applied
        coupon_id = None
        if quote.coupon_applied:
            coupon_res = await self.coupon_service.validate_and_calculate(
                code=quote.coupon_applied,
                user_id=user_id,
                subtotal=quote.subtotal,
            )
            coupon_id = coupon_res.coupon_id

        # Determine initial booking status:
        # If total is 0 or payment will be handled, set status CONFIRMED or PAYMENT_PENDING
        initial_status = "CONFIRMED"

        booking = await self.repo.create_booking(
            user_id=user_id,
            mode=data.mode,
            centre_id=data.centre_id,
            address_id=data.address_id,
            slot_id=data.slot_id,
            status=initial_status,
            subtotal=quote.subtotal,
            discount=quote.discount,
            collection_fee=quote.collection_fee,
            total=quote.total,
            coupon_id=coupon_id,
            source=source,
            idempotency_key=data.idempotency_key,
            patient_notes=data.patient_notes,
        )

        # Create item snapshots
        for qi in quote.items:
            await self.repo.add_item(
                booking_id=booking.id,
                patient_id=qi.patient_id,
                item_type=qi.item_type,
                item_id=qi.item_id,
                name_snapshot=qi.name,
                price_snapshot=qi.price,
                mrp_snapshot=qi.mrp,
            )

        # Record coupon usage if applied
        if coupon_id and quote.discount > 0:
            await self.coupon_service.repo.record_usage(
                coupon_id=coupon_id,
                booking_id=booking.id,
                user_id=user_id,
                amount=quote.discount,
            )

        # Emit transactional outbox event
        emit(
            self.session,
            topic="booking.created",
            payload={
                "booking_id": str(booking.id),
                "booking_code": booking.booking_code,
                "user_id": str(booking.user_id),
                "total": booking.total,
                "mode": booking.mode,
            },
        )

        reloaded = await self.repo.get_by_id(booking.id)
        assert reloaded is not None
        return self._to_response(reloaded)

    async def get_booking(
        self, booking_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> BookingResponse:
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise NotFound("Booking not found")
        if user_id and booking.user_id != user_id:
            raise PermissionDenied("Access denied to this booking")
        return self._to_response(booking)

    async def list_user_bookings(self, user_id: uuid.UUID) -> list[BookingResponse]:
        bookings = await self.repo.list_for_user(user_id)
        return [self._to_response(b) for b in bookings]

    async def list_all_bookings(
        self,
        *,
        status: str | None = None,
        mode: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BookingResponse], int]:
        bookings = await self.repo.list_all(status=status, mode=mode, limit=limit, offset=offset)
        total = await self.repo.count_all(status=status, mode=mode)
        return [self._to_response(b) for b in bookings], total

    async def cancel_booking(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None = None,
    ) -> BookingResponse:
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise NotFound("Booking not found")
        if booking.user_id != user_id:
            raise PermissionDenied("Access denied to cancel this booking")

        if booking.status in ("CANCELLED", "REFUNDED", "DELIVERED"):
            return self._to_response(booking)

        # Release slot capacity if applicable
        if booking.slot_id:
            slot = await self.scheduling_repo.get_slot_for_update(booking.slot_id)
            if slot and slot.booked > 0:
                slot.booked -= 1

        await self.repo.update_status(
            booking=booking,
            to_status="CANCELLED",
            actor_user_id=user_id,
            reason=reason or "Cancelled by patient",
        )

        emit(
            self.session,
            topic="booking.cancelled",
            payload={
                "booking_id": str(booking.id),
                "booking_code": booking.booking_code,
                "reason": reason,
            },
        )

        reloaded = await self.repo.get_by_id(booking.id)
        assert reloaded is not None
        return self._to_response(reloaded)

    async def update_status_admin(
        self,
        booking_id: uuid.UUID,
        to_status: str,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> BookingResponse:
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise NotFound("Booking not found")

        await self.repo.update_status(
            booking=booking,
            to_status=to_status,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        reloaded = await self.repo.get_by_id(booking.id)
        assert reloaded is not None
        return self._to_response(reloaded)

    def _to_response(self, b: Booking) -> BookingResponse:
        return BookingResponse(
            id=b.id,
            booking_code=b.booking_code,
            user_id=b.user_id,
            mode=b.mode,
            centre_id=b.centre_id,
            address_id=b.address_id,
            slot_id=b.slot_id,
            status=b.status,
            subtotal=b.subtotal,
            discount=b.discount,
            collection_fee=b.collection_fee,
            total=b.total,
            coupon_id=b.coupon_id,
            source=b.source,
            patient_notes=b.patient_notes,
            version=b.version,
            created_at=b.created_at,
            updated_at=b.updated_at,
            items=[
                BookingItemResponse(
                    id=item.id,
                    patient_id=item.patient_id,
                    item_type=item.item_type,
                    item_id=item.item_id,
                    name_snapshot=item.name_snapshot,
                    price_snapshot=item.price_snapshot,
                    mrp_snapshot=item.mrp_snapshot,
                    status=item.status,
                )
                for item in b.items
            ],
            status_history=[
                BookingStatusHistoryResponse(
                    id=h.id,
                    from_status=h.from_status,
                    to_status=h.to_status,
                    reason=h.reason,
                    created_at=h.created_at,
                )
                for h in b.status_history
            ],
        )
