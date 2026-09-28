# Phase 3 report: Booking, Scheduling & Payment

**Date:** 2026-09-27 · **Scope:** patient profiles & family management, addresses, slot capacity & locking engine, quote calculation, coupon validation engine, booking state machine & lifecycle, payment provider abstraction (SSLCommerz sandbox + Cash), reactive shopping cart, 5-step patient checkout wizard, patient booking history & account management, and console booking operations.

## Completed

- **Database & Schemas:**
  - `patient`: `patient_profiles`, `patient_family_members`, `patient_addresses`.
  - `scheduling`: `slot_templates`, `slots` (with capacity tracking and concurrency protection), `slot_holds`.
  - `coupon`: `coupons`, `coupon_usages` (with discount rules, minimum order, per-user limits, and validity checks).
  - `booking`: `bookings`, `booking_items`, `booking_item_parameters`, `booking_status_history` (with immutable price snapshots, UUID tokens, and strict status state machine).
  - `payment`: `payments`, `payment_transactions` (with idempotency, webhook signature verification, and gateway abstraction).
  - `0003_patient_scheduling_booking_payment` migration with full rollback support.
- **Concurrency & Slot Locking:**
  - Row-level `SELECT ... FOR UPDATE` on slot capacity during hold creation and booking confirmation.
  - Temporary hold expiry handling to prevent slot starvation.
- **Payment Gateway Integration:**
  - Extensible `PaymentProvider` interface.
  - `SSLCommerzProvider` with session initialization, redirect URL generation, IPN validation, and sandbox support.
  - `CashPaymentProvider` for home sample collection and walk-in cash payments.
- **Shared App Core (`packages/app-core`):**
  - Persistent `CartProvider` and `useCart` hook supporting item additions, duplicate prevention, reactive price computation, and drawer state.
- **Public & Patient Web (`apps/web`):**
  - Interactive shopping cart drawer (`CartDrawer`) accessible from any page.
  - 5-step Booking Wizard (`/book`):
    1. Patient selection (Self or Family Member).
    2. Service Mode (Home Collection or Centre Visit) & Address selection.
    3. Slot Calendar & Time Picker.
    4. Review Order & Promo Coupon validation.
    5. Payment Method selection & confirmation.
  - Patient Account Portal (`/account/bookings`, `/account/family`, `/account/addresses`).
- **Staff Console (`apps/console`):**
  - Operations bookings management (`/bookings`) with real-time status badges, patient info, payment mode, and order timeline.
- **Testing & Quality Gates:**
  - 105 passed pytest test suite including slot concurrency, quote calculations, and coupon rules.
  - Monorepo TS typecheck and production build clean across all packages.
  - Import-linter architecture contracts verified (7/7 kept).
