# Product Requirements Document

**Product (working name):** Nirnoy Diagnostics — *placeholder; needs a trademark check before launch*
**Status:** Draft for approval · 2026-09-26

## 1. Vision

A diagnostic laboratory platform for Bangladesh that takes a patient from "I need a test" to a verified, authenticated report with minimal friction, and gives the lab a traceable, auditable operation from sample to signature.

## 2. Personas

| Persona | Goal | Primary surface |
|---|---|---|
| **Patient** (urban, mobile-first, Bangla or English) | Book fast, get the report on the phone | Web (mobile) |
| **Family member** (dependant, often no phone of their own) | Be booked for by the account holder | via Patient |
| **Collector / phlebotomist** | Clear daily route; collect and label correctly | Console (mobile) |
| **Receptionist** | Walk-in registration, billing, sample accession at centre | Console |
| **Lab technician** | Worklist, enter results, flag issues | Console (desktop) |
| **Pathologist** | Review, verify, sign; handle criticals | Console |
| **Doctor** (referring) | View reports for their referred patients (with consent) | Console (P2) |
| **Admin / Super admin** | Configure everything; see everything they are allowed to | Console |
| **Branch manager** | Branch operations, slots, staff, performance | Console |
| **Corporate admin** | Employee health programmes, invoices | Console (corporate shell) |
| **Partner** (collection centre / clinic) | Refer and book, track, get paid commission | Console (partner shell) |
| **Accountant** | Invoices, refunds, reconciliation, AR/AP | Console |
| **Support agent** | Resolve tickets tied to bookings and payments | Console |

## 3. Functional requirements (by module)

Numbered **FR-{module}-{n}**. Acceptance criteria are summarised; full criteria live with the user stories in §5.

### AUTH
- FR-AUTH-1 Register and log in with a BD mobile number + OTP (primary) or email + password.
- FR-AUTH-2 OTPs: 6 digits, 5-minute TTL, max 5 attempts, max 3 sends per 15 minutes per phone and per IP.
- FR-AUTH-3 Access JWT (15 min) plus a rotating refresh token (30 days) with reuse detection that revokes the whole token family.
- FR-AUTH-4 Session/device list and remote logout.
- FR-AUTH-5 Password reset via OTP or email link. Argon2id hashing.
- FR-AUTH-6 Staff accounts require password + OTP (2FA). Patients may use OTP only.

### RBAC
- FR-RBAC-1 16 roles as specified. Permissions are granular (`resource:action`) and assignable to roles; roles are assignable per user **per scope** (global / branch / lab / corporate / partner).
- FR-RBAC-2 Every API enforces permission + scope on the server. Frontend visibility is cosmetic only.
- FR-RBAC-3 Row-level rules: collectors see only their assignments; partners only their data; corporate admins never see results without employee consent.

### CATALOG / PACKAGES / SEARCH
- FR-CAT-1 Test CRUD with every field in the brief. Prices are stored per branch (with a default price list).
- FR-CAT-2 Parameters with reference ranges keyed by sex, age band (in days), sample type, lab and method/equipment, plus critical low/high.
- FR-CAT-3 Packages built from tests, with targeting (sex, age, concern), pricing and a computed "you save".
- FR-CAT-4 Search over tests, packages, concerns, articles and centres, with synonyms ("sugar" → glucose), Bangla terms and typo tolerance (trigram). Autocomplete under 150 ms p95 (cached).
- FR-CAT-5 Health concerns: a patient-friendly taxonomy mapped many-to-many to tests and packages.

### BOOKING
- FR-BKG-1 Cart → patient(s) → collection mode → address/centre → date → slot → coupon → payment → confirmation.
- FR-BKG-2 One booking can include items for several family members at the same address/slot (common household case). Each item carries its `patient_id`.
- FR-BKG-3 Explicit state machine (see `architecture.md` §6). Every transition is recorded in `booking_status_history`.
- FR-BKG-4 Slot capacity is enforced transactionally. Held slots expire after 10 minutes if unpaid.
- FR-BKG-5 Reschedule and cancel follow cut-off rules configured per branch.
- FR-BKG-6 Home collection fee is configurable (per zone, waiver threshold).

### PAYMENT / COUPON
- FR-PAY-1 Gateway-agnostic `PaymentProvider` interface. Adapters: SSLCommerz, bKash, Nagad, Cash.
- FR-PAY-2 Status is **only** changed by server-side verification (callback + verify API). Callbacks are idempotent on the provider transaction ID.
- FR-PAY-3 Full and partial refunds, tracked against the original transaction.
- FR-CPN-1 Coupon rules: percentage/fixed, first-booking, test/package/centre/corporate/user scope, minimum amount, maximum discount, global and per-user limits, validity window. Validated server-side at quote time **and** at confirmation time.

### COLLECTION / SAMPLE
- FR-COL-1 Auto-assign (zone + capacity + load) with manual override.
- FR-COL-2 Collector flow: accept → on the way → arrived → verify patient (name + DOB + OTP or ID) → collect → label (barcode per container) → complete.
- FR-SMP-1 Barcode format `SMP-YYYY-NNNNNN` (sequence per year). Printable Code-128.
- FR-SMP-2 Chain of custody: every hand-off is a `sample_event` (collected, in-transit, received, processing, completed, rejected, disposed).
- FR-SMP-3 Rejection with a coded reason triggers a recollection booking at no charge (configurable) and notifies the patient.

### LAB / RESULT / VERIFICATION
- FR-LAB-1 Department worklists (pending, processing, completed, rejected, critical, pending verification).
- FR-RES-1 Parameter-level result entry. The flag (N/L/H/critical-L/critical-H) is computed server-side from the matching reference range; the matched range is snapshotted with the result.
- FR-RES-2 Critical values trigger immediate notification to the pathologist and lab manager, plus an audit entry. No patient-facing interpretation.
- FR-VER-1 Pathologist approves or rejects. Rejection returns the result to the technician with a reason. Edits by a pathologist are versioned and audited.
- FR-VER-2 Only users holding `result:verify` for that lab/department can verify. The same user cannot enter **and** verify the same result (configurable four-eyes rule).

### REPORT
- FR-RPT-1 PDF generated asynchronously after all items in a lab order are verified. Partial reports are allowed (configurable).
- FR-RPT-2 Immutable versions: amendments create version n+1 with a reason. Earlier versions stay retrievable and are marked "superseded".
- FR-RPT-3 QR code links to `/verify/{opaque_token}`. The public page shows only authenticity, report code, issue date, lab, and masked patient initials + age/sex.
- FR-RPT-4 Download via short-lived signed URL. Share link with expiry (default 7 days) and revocation.
- FR-RPT-5 Guest retrieval: report code + OTP to the phone on file.

### PATIENT PORTAL
- FR-PP-1 Dashboard, family members (relationship, DOB, sex, blood group, phone optional), addresses, bookings, reports, payments, prescriptions, notifications, tickets.
- FR-PP-2 Health timeline and trend charts for numeric parameters with the same LOINC/parameter code and unit. Chart shows the reference band. **No interpretation text.**

### PRESCRIPTION
- FR-RX-1 Upload JPG/PNG/PDF ≤ 10 MB, up to 5 files. Validated by magic bytes.
- FR-RX-2 Advisor queue → recommended items → quotation → patient accepts → booking created.

### CORPORATE / PARTNER
- FR-CORP-1 Employee roster (CSV import), eligibility per package, bulk scheduling (camp or individual), consolidated monthly invoice.
- FR-CORP-2 Employer sees attendance/completion only. Result visibility requires an explicit, revocable per-employee consent record.
- FR-PTN-1 Partner users register patients and book on their behalf. Commission rules (percentage/fixed, by test/category/package, date-effective) are applied at invoice time and recorded immutably.

### INVENTORY / FINANCE / CRM / NOTIFICATION / CMS / ANALYTICS
- FR-INV-1 Items, batches with expiry, stock movements (append-only ledger), per-location stock, minimum levels, POs. Low-stock and expiry alerts (daily job).
- FR-FIN-1 Invoice per booking (or per corporate period), payments, refunds, expenses, AR/AP, revenue by branch/day. Money in poisha (bigint).
- FR-CRM-1 Tickets with categories, priority, SLA timers, assignment, threaded messages and attachments.
- FR-NTF-1 Event → template (per channel, per language) → provider. Logged with delivery status. Patient channel preferences respected (transactional messages always go out).
- FR-CMS-1 Banners, pages, FAQs, blogs, testimonials, promotions, health concerns. Draft/published with a scheduled publish time.
- FR-ANL-1 Admin dashboard KPIs and charts from daily aggregate tables, refreshed by a scheduled job. Near-real-time counters for "today".

## 4. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 Performance | Public catalog pages LCP < 2.5 s on 4G mid-range Android; API p95 < 300 ms for reads, < 800 ms for booking create |
| NFR-2 Availability | 99.5 % for the patient web/API at launch |
| NFR-3 Security | OWASP ASVS L2 targets; see `architecture.md` §9 |
| NFR-4 Privacy | Data minimisation; consent records; audit of every PHI read in staff consoles (report/result views) |
| NFR-5 Scale (design target) | 1M patients, 5k bookings/day, 20k tests/parameters, 50 branches |
| NFR-6 Accessibility | WCAG 2.2 AA on the patient web |
| NFR-7 i18n | All UI strings externalised; en + bn at launch |
| NFR-8 Observability | JSON logs with request_id, Prometheus metrics, Sentry, `/health` `/ready` `/live` |
| NFR-9 Recoverability | Daily PG base backup + WAL archiving (PITR), RPO ≤ 15 min, RTO ≤ 4 h; object storage versioning |
| NFR-10 Retention | Reports and results retained ≥ 10 years (configurable, pending legal confirmation) |

## 5. Key user stories and acceptance criteria

**US-1 Book home collection for a parent**
*As a patient, I want to book a fasting test for my mother at home tomorrow morning.*
- Given the catalog, when I search "sugar", then FBS, HbA1c and diabetes packages appear.
- I can add my mother as a family member inside the flow without leaving it.
- Only slots with remaining capacity in her address zone are selectable, and the fasting preparation note is shown before payment.
- After bKash payment the server verifies it, the booking is `CONFIRMED`, and I get an SMS in my chosen language.

**US-2 Collector completes an assignment**
- The assignment list shows only mine, ordered by slot time.
- I cannot mark "collected" before "patient verified".
- Each container gets a unique barcode. Tests map to containers by sample type.
- Offline: actions queue locally and sync, with the server rejecting out-of-order transitions.

**US-3 Technician enters a critical potassium**
- Entering K = 6.8 mmol/L (critical high for the matched adult range) flags `CRITICAL_HIGH`.
- The pathologist and lab manager are notified within 60 s. An audit record exists.
- The patient receives nothing until verification.

**US-4 Pathologist amends a released report**
- Editing a released report requires a reason. Version 2 is generated, version 1 is marked superseded, and the patient is notified of the amended report.
- QR verification of v1 shows "superseded by a newer version".

**US-5 Corporate admin views programme status**
- Sees employees scheduled/completed. Sees results only for employees with active consent.

(Remaining stories for partner, finance, inventory, CMS and support follow the same Given/When/Then pattern and will be written per phase.)

## 6. Business rules

1. A booking becomes `CONFIRMED` only after a verified payment, **or** when the payment method is Cash and the branch allows cash.
2. `CANCELLED` bookings cannot transition to any collection state.
3. Samples with any event beyond `COLLECTED` cannot be deleted, only marked disposed/rejected.
4. Finalised reports are immutable. Changes create a new version.
5. Only users with `result:verify` in scope may verify. The four-eyes rule is on by default.
6. Payment callbacks are idempotent. A payment amount mismatch marks the payment `FAILED` and raises an alert.
7. Coupons are re-validated at confirmation. Usage is recorded in the same transaction as confirmation.
8. Collectors can read patient data only for their active assignments (and for 24 h after completion).
9. Partners and corporates are data-scoped by `partner_id`/`corporate_id`.
10. Prices, TAT, ranges, fees, commissions, slots, hours and templates all live in the database. **No business constants in code.**
11. Every price shown at checkout is the server-computed quote. The client never sends prices.
12. No automated diagnosis or clinical advice anywhere. AI features (future) are labelled and advisory, with staff in the loop.

## 7. Out of scope (v1)

Native mobile apps (the API is designed for them), instrument interfacing (HL7/ASTM — architecture leaves a hook), insurance claims, teleconsultation, and doctor e-prescribing.

## 8. Open questions (need your input)

1. Brand name and logo — or keep the placeholder for now?
2. Which payment gateway merchant accounts exist or are expected (SSLCommerz first?).
3. SMS provider (e.g. SSL Wireless, Alpha SMS, BulkSMSBD)?
4. Hosting target (AWS ap-south-1/Singapore, local BD data centre?). Data residency requirements?
5. Is the first rollout one branch + one lab, or multi-branch from day one?
6. Are digital signatures a scanned-signature image + audit trail (typical), or PKI-based (e.g. a BD CCA-licensed certificate)?
