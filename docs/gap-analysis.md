# Gap Analysis

Compares the observable reference functionality (`reference-analysis.md`) with the target platform. Priority: **P0** = MVP (needed for the end-to-end patient → report flow), **P1** = launch, **P2** = post-launch.

## 1. Missing features

| Area | Gap | Priority |
|---|---|---|
| Identity | No patient accounts, sessions or family profiles | P0 |
| Booking | No visible slot selection, capacity control or home-vs-centre choice in one flow | P0 |
| Payments | No visible online payment; BD gateways needed | P0 |
| Tracking | No booking/sample status for patients | P0 |
| Reports | Lab-no.+password only; no history, versioning or authenticity check | P0 |
| Lab ops | No LIS, sample custody, result entry or verification (not public, but we must build it) | P0 |
| Collector | No field workflow | P0 |
| Prescription | Lead form only; no quotation loop | P1 |
| Coupons | Promotions page only; no rule engine | P1 |
| Notifications | None visible (SMS/email/in-app) | P0 (SMS), P1 (email/in-app), P2 (push) |
| Corporate | Brochure only | P1 |
| Partner | Brochure only; no commissions | P1 |
| Inventory / finance | None | P1 |
| CRM | Contact form only | P1 |
| Health timeline / trends | None | P2 |
| i18n | English only | P1 |
| Blog | External | P1 |

## 2. UX problems

- Tests and packages share one list, so comparing packages is hard. **Fix:** separate package pages with an "included tests" breakdown and per-test value.
- The condition taxonomy uses clinical labels ("Disorders of Haemopoiesis"). **Fix:** plain-language health concerns for patients, clinical taxonomy kept for staff and SEO.
- Home collection is a form followed by a callback, which adds friction and delay. **Fix:** instant booking with a slot, with callback as a fallback.
- Report retrieval depends on a paper receipt password. **Fix:** portal access and SMS-delivered secure links, with guest retrieval kept.
- Much of the site is client-rendered, which hurts SEO and first paint on slow mobile networks. **Fix:** pre-rendered public catalog pages (see architecture §SEO).

## 3. Scalability concerns

- Catalog size: thousands of tests, each with parameters and reference ranges. Needs indexed full-text search, cursor/offset pagination and Redis caching.
- Slot contention at peak morning hours (fasting tests). Needs row-level capacity locking.
- Report PDF generation must be asynchronous (Celery) and idempotent.
- Multi-branch and multi-lab: every operational row carries `branch_id`/`lab_id` from day one.

## 4. Security concerns

- Lab-number + short password retrieval can be brute-forced. **Mitigation:** rate limits, a long random access token, OTP to the registered phone, and audit logging.
- Health data is sensitive (Bangladesh Digital Security / Personal Data Protection regime is evolving). **Mitigation:** encryption in transit and at rest, least privilege, full audit trail, data-minimised QR verification.
- Payment callbacks must be server-verified and idempotent.
- Uploads (prescriptions) need signature checks, size limits and private buckets.

## 5. Bangladesh-specific requirements

- Currency: BDT (৳). Store money as integer **poisha** (1/100 BDT) to avoid float errors.
- Phone: `+8801[3-9]XXXXXXXX` validation. SMS OTP is the primary login method (email is secondary).
- Addresses: Division → District → Upazila/Thana → Area, plus house/road/block/landmark (landmarks matter for collectors).
- Payments: bKash, Nagad, SSLCommerz (cards + MFS aggregator), Cash on collection.
- Language: Bangla + English, including Bangla numerals as a display option.
- Working week: Friday weekend (with Saturday partial at some branches) and a holiday calendar (Eid dates vary), configured per branch.
- Low-bandwidth and low-end Android devices: small JS bundles and a collector UI that works on flaky connections.

## 6. Requirements by stakeholder

| Stakeholder | Key needs |
|---|---|
| Admin | Configurable catalog, pricing, slots, coupons, templates, RBAC; bulk import/export; audit log |
| Lab | Barcode-driven accession, worklists by department, reference-range engine, critical alerts, verification queue, rejection + recollection |
| Patient | 6-step mobile booking, family profiles, tracking, reports + trends, Bangla |
| Corporate | Employee roster, bulk package booking, consolidated invoicing, **consent-gated** report visibility |
| Partner | Register patients, book, track samples, commission statements |
| Finance | Invoices, refunds, receivables/payables, reconciliation with gateway settlements |
| Support | Tickets linked to bookings/payments, SLA view |
