# Architecture

**Status:** Proposal for approval · 2026-09-26

## 1. Key decisions (ADR summary)

| # | Decision | Rationale |
|---|---|---|
| ADR-1 | **Modular monolith** at launch: one FastAPI codebase and one deployable API image, split into ~18 bounded-context modules with enforced boundaries. Celery workers run from the same image. | The brief asks for service boundaries *without* premature distribution. A single deployable removes distributed transactions (booking + slot + coupon + payment must commit atomically), network hops and cross-service auth while the domain is still settling. Boundaries are enforced by import-linter contracts, so modules can be extracted later. |
| ADR-2 | **Gateway = Nginx (edge) + FastAPI middleware layer.** | Nginx does TLS, rate-limit buckets, body-size limits, CORS preflight caching and static assets. The app layer does JWT auth, RBAC, request IDs, error normalisation and versioning (`/api/v1`). A separate gateway process is only worth it once services are extracted; Nginx config is already written for that. |
| ADR-3 | **Two frontend apps in a pnpm monorepo:** `apps/web` (public site + patient portal) and `apps/console` (all staff, collector, corporate and partner shells, route-guarded by role). Shared `packages/ui` (design system), `packages/api-client` (generated from OpenAPI) and `packages/i18n`. | Admin, partner and corporate share 80 % of their components (tables, forms, drawers). Three apps would triplicate the auth/layout code. The public web has different needs (SEO, bundle size), so it stays separate. |
| ADR-4 | **SEO:** `apps/web` uses Vite + React Router with **build-time and on-demand prerendering** of catalog, package, concern, article and centre pages (vite-plugin-ssr / `vike`), hydrating to an SPA. | The brief fixes React + Vite. Pure SPA pages are weak for SEO, which matters here because test pages drive acquisition. Fallback option if prerendering proves awkward: Next.js for `apps/web` only (needs your approval). |
| ADR-5 | PostgreSQL 16 (one cluster). **One schema per module** (`auth`, `catalog`, `booking`, …). A module may FK into another module's tables only for stable identity references (e.g. `patient_id`) and never writes to another module's schema. | Keeps logical ownership visible and makes later extraction mechanical. |
| ADR-6 | Money as `BIGINT` poisha; time as `timestamptz` (UTC); display in Asia/Dhaka. | Correctness. |
| ADR-7 | IDs: `UUIDv7` primary keys (time-ordered, index-friendly). Human codes (`BKG-2026-000123`, `SMP-…`, `RPT-…`) come from per-year sequences. | UUIDs are safe to expose. Codes are staff-friendly. |
| ADR-8 | Internal domain events via a transactional **outbox** table, relayed by Celery to handlers (notifications, analytics, report generation). | Reliable side effects without a message broker at launch. Kafka/RabbitMQ can replace the relay later. |
| ADR-9 | Report PDFs: **WeasyPrint** (HTML/CSS → PDF, with Bangla font support via Noto Sans Bengali) rendered in a worker. | Templates are editable HTML. Bangla shaping works with Pango. |

## 2. System context

```
                 ┌──────────────── Internet ────────────────┐
 Patients ──► apps/web ─┐                                    │
 Staff/Collectors/      │    HTTPS                           │
 Corporate/Partners ──► apps/console ──► Nginx (edge/gateway)│
 Payment gateways ─ callbacks ───────►   │  TLS, rate-limit, │
                                         │  CORS, size limits│
                                         ▼                   │
                         ┌──────── API (FastAPI, /api/v1) ─────────┐
                         │ middleware: request-id → auth → rbac →  │
                         │ idempotency → error normaliser → log    │
                         │ modules: auth, patient, catalog, …      │
                         └──┬─────────┬──────────┬──────────┬──────┘
                            │         │          │          │
                       PostgreSQL   Redis      S3 storage outbox
                                      ▲                     │
                                      └── Celery workers ◄──┘ (+ beat)
                                            │ SMS / Email / Push / PDF
```

## 3. Module boundaries

| Module | Owns (schema) | Depends on (read via service interface) |
|---|---|---|
| `auth` | users, credentials, sessions, refresh tokens, OTP (Redis), roles, permissions, user_roles | — |
| `patient` | patients, family links, addresses, consents | auth |
| `catalog` | departments, categories, sample types, tests, parameters, reference ranges, packages, health concerns, price lists | — |
| `centre` | branches, centres, labs, services, hours, holidays, zones | catalog |
| `scheduling` | slot templates, slot instances, capacity, holds | centre |
| `booking` | bookings, items, status history, quotes | patient, catalog, scheduling, coupon, payment (interface) |
| `coupon` | coupons, rules, usage | catalog |
| `payment` | payments, transactions, callbacks, refunds, provider adapters | — (booking subscribes to its events) |
| `billing` | invoices, items, AR/AP, expenses, commissions ledger | booking, payment, partner, corporate |
| `collection` | collectors, assignments, collection events | booking, patient |
| `sample` | samples, barcodes, events, transfers, rejections | booking, catalog |
| `lab` | lab orders, items, worklists, instruments (future) | sample, catalog |
| `result` | results, parameters, comments, verification | lab, catalog |
| `report` | reports, versions, signatures, verification tokens, shares | result, patient |
| `prescription` | prescriptions, files, quotations | patient, catalog |
| `corporate` | corporates, users, employees, contracts, consents | patient, catalog |
| `partner` | partners, users, commission rules | patient |
| `inventory` | items, batches, stock movements, suppliers, POs | centre |
| `support` | tickets, messages | patient |
| `notification` | templates, logs, preferences, devices | — (consumes events) |
| `cms` | pages, banners, blogs, FAQs, testimonials, promotions, media | catalog |
| `audit` | audit_logs (append-only) | — |
| `analytics` | daily aggregates (materialised) | reads replicas / events |

**Rule:** a module exposes `service.py` (public API) and `events.py`. Other modules import only those. This is enforced by `import-linter` in CI.

## 4. Backend layering (per module)

```
modules/booking/
  api.py          # FastAPI router: HTTP ↔ schemas, permission deps
  schemas.py      # Pydantic request/response models
  service.py      # use-cases; transaction boundaries; the ONLY public entry
  domain.py       # entities, enums, state machine, pure rules
  repository.py   # SQLAlchemy 2 queries
  models.py       # ORM tables (schema="booking")
  events.py       # domain event dataclasses
  tasks.py        # Celery tasks
  tests/
```

- Dependency injection via FastAPI `Depends` (session, current user, service factories).
- One DB transaction per request use-case (`async with uow:`). Outbox rows are written in the same transaction.
- Async SQLAlchemy (asyncpg). Pool tuned per container. PgBouncer in production.

## 5. Request flow (example: create booking)

1. Nginx: TLS, `limit_req` zone `api`, 1 MB body cap, forwards `X-Request-ID` (generates one if missing).
2. Middleware: binds request_id to the log context → verifies the JWT → loads the principal (user id, roles, scopes; cached in Redis for 60 s, invalidated on role/status change).

   *Signing (as implemented in Phase 1):* HS256 with `JWT_SECRET`, because the monolith both issues and verifies tokens. When a service is extracted or third parties must verify tokens, switch to EdDSA with a published JWKS and `kid` rotation. Only `app/core/security.py` changes.
3. Route dependency `require("booking:create")` checks permission + scope.
4. `Idempotency-Key` header (required on POST booking/payment): Redis `SET NX` stores the key with the request hash. A replay returns the stored response; a different body under the same key returns `409 IDEMPOTENCY_KEY_REUSED`.
5. `BookingService.create()`:
   - re-price the cart from the price list (client prices ignored)
   - validate the coupon
   - `SELECT … FOR UPDATE` on the `slot_instance` row → check `booked + held < capacity` → increment `held`
   - insert booking (`PAYMENT_PENDING`, or `CONFIRMED` for eligible cash), items, status history, outbox event
   - commit.
6. Response wrapped in the standard envelope. Errors mapped to stable codes.

## 6. State machines (declared in code as enums + transition tables; shared with the frontend via OpenAPI)

**Booking**

```
CREATED → PAYMENT_PENDING → CONFIRMED ─┬→ COLLECTOR_ASSIGNED → COLLECTION_STARTED → SAMPLE_COLLECTED
            │        ▲                 │                                              │
            ▼        │ (retry)         └→ (centre) SAMPLE_COLLECTED                   ▼
       PAYMENT_FAILED┘                                        LAB_RECEIVED → PROCESSING → RESULT_READY
 CONFIRMED/COLLECTOR_ASSIGNED ↔ RESCHEDULED (returns to CONFIRMED)                     ↓
 any pre-collection state → CANCELLED → REFUNDED (if paid)          VERIFIED → REPORT_GENERATED → DELIVERED
```

- Booking status is an **aggregate projection**: sample and result events advance it (e.g. booking reaches `PROCESSING` when the first sample is processing, and `REPORT_GENERATED` when all items are reported). Items keep their own granular status.

**Collection assignment:** PENDING → ASSIGNED → ACCEPTED → ON_THE_WAY → ARRIVED → COLLECTED; CANCELLED from any pre-COLLECTED state.

**Sample:** CREATED(labelled) → COLLECTED → IN_TRANSIT → RECEIVED → PROCESSING → COMPLETED → DISPOSED; REJECTED from COLLECTED..PROCESSING (→ spawns recollection).

**Result:** DRAFT → ENTERED → (auto-validation) → PENDING_VERIFICATION → VERIFIED | RETURNED(→ENTERED); VERIFIED → AMENDED (new version).

**Report:** GENERATING → FINAL → SUPERSEDED (when a new version is final). Delivered-ness is tracked by delivery events, not by status.

Invalid transitions raise `INVALID_STATE_TRANSITION` (409). Each transition writes `*_status_history` with actor, reason and timestamp.

## 7. Auth and authorisation

- **Tokens:** access JWT (15 min, claims `sub`, `sid`, `roles` summary, `ver`). Refresh token = opaque 256-bit random value, stored hashed, rotated on every use, grouped by `family_id`. Reuse of a rotated token revokes the family (theft detection).
- **Storage:**
  - `apps/web`: refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie scoped to `/api/v1/auth/refresh`; access token in memory only.
  - `apps/console`: same, plus 2FA.
  - Mobile (future): secure storage, sent in the body.
- **CSRF:** the refresh cookie is SameSite=Strict and the path is limited. All other endpoints use a Bearer header, so CSRF does not apply.
- **OTP:** stored as an HMAC in Redis (`otp:{purpose}:{phone}`) with TTL and an attempt counter. Never logged.
- **RBAC model:** `permission(code)`, `role`, `role_permission`, `user_role(user_id, role_id, scope_type, scope_id)`. The check is `has(user, perm, resource_scope)`. Row-level filters are applied in repositories via a `ScopeFilter` built from the principal (collector → assignment ids; partner → partner_id; …).
- **PHI read audit:** endpoints that return results/reports in staff consoles emit `audit(action="READ")`.

## 8. Data, caching, storage, jobs

- **Redis (not a source of truth):** OTP, rate-limit counters (app-level per user/phone), idempotency keys (24 h), principal cache, catalog/search caches (versioned keys, invalidated on publish), slot availability cache (short TTL; the DB is authoritative), Celery broker.
- **Object storage (S3-compatible: SeaweedFS locally → AWS S3 or equivalent in production; buckets bootstrapped by `app.scripts.init_storage`):** buckets `prescriptions`, `reports`, `invoices`, `attachments` (private, SSE enabled) and `cms-public` (public-read via CDN). Keys are server-generated UUIDs. Downloads use presigned GETs (≤ 5 min). Uploads are streamed through the API for validation (magic bytes, size, type) then put. AV scanning (ClamAV sidecar) is a P1 hook.
- **Celery queues:** `critical` (critical-result alerts, OTP SMS), `default` (notifications, outbox relay), `reports` (PDF), `batch` (analytics, expiry/low-stock, cleanup). Beat schedules the periodic jobs. Tasks are idempotent (keyed by entity + version).

## 9. Security architecture

| Concern | Control |
|---|---|
| Transport | TLS 1.2+ at Nginx, HSTS, and TLS to PG/Redis in production |
| At rest | Disk/volume encryption (cloud KMS); S3 SSE; column-level pgcrypto for NID/passport numbers if collected |
| Passwords | Argon2id (argon2-cffi, tuned ~50 ms) |
| Injection | SQLAlchemy bound parameters only; no raw string SQL; Pydantic validation at the edge |
| XSS | React escaping; CMS rich text sanitised server-side (nh3/bleach allow-list); CSP with nonces |
| Rate limits | Nginx per IP; app per phone/user for OTP, login, report retrieval and verify pages |
| Secrets | Env vars via the platform secret manager; `.env` git-ignored; gitleaks in CI |
| Headers | CSP, X-Content-Type-Options, Referrer-Policy, frame-ancestors none |
| Payment | Server-to-server verify API, signature/hash validation per provider, amount + currency match, idempotent processing |
| Files | Extension + MIME + magic bytes; ≤ 10 MB; re-encode images (strip EXIF); PDFs rejected if they contain JavaScript/embedded files |
| Audit | Append-only `audit.audit_logs` (REVOKE UPDATE/DELETE from the app role; a trigger blocks mutation); optional hash chain |
| Logging | structlog JSON; redaction processor for `password`, `otp`, `token`, `authorization`, `card`, result values |
| Dependencies | pip-audit, pnpm audit, Trivy image scan, CodeQL |

## 10. Payment architecture

```python
class PaymentProvider(Protocol):
    code: str
    async def create_payment(self, p: PaymentIntent) -> ProviderInit: ...       # returns redirect URL / token
    async def verify_payment(self, provider_ref: str) -> ProviderStatus: ...    # server-to-server
    async def parse_callback(self, req: RawCallback) -> CallbackData: ...       # signature check
    async def refund_payment(self, r: RefundRequest) -> ProviderRefund: ...
    async def get_payment_status(self, provider_ref: str) -> ProviderStatus: ...
```

- The registry maps `payment_method → provider`, enabled per branch in `system_settings`.
- Flow: booking → `PaymentService.create(intent)` → redirect. The callback/IPN is stored raw in `payment_callbacks` (unique on provider + provider_txn_id + event) → `verify_payment` → state change → outbox `PaymentSucceeded` → booking confirms. The frontend return URL only **polls** status.
- A reconciliation job re-verifies `PENDING` payments older than 15 minutes, and expires holds.

## 11. Notification architecture

Event (outbox) → `NotificationRouter` resolves recipients + channels (preferences, transactional override) → renders `notification_templates` (key, channel, locale, versioned Jinja2 sandboxed) → provider adapter (SMS / SMTP or SES / FCM / in-app table) → `notification_logs` (status, provider id, retries with backoff). Templates never contain result values; they link to the portal.

## 12. Observability and ops

- `/health` (process up), `/live`, `/ready` (PG + Redis + S3 reachable).
- Prometheus metrics (`prometheus-fastapi-instrumentator` + custom business counters: bookings, payments by status, critical alerts, report TAT histogram). Grafana dashboards. Sentry for API, workers and both frontends (PII scrubbing on).
- Docker Compose: `docker-compose.yml` (base), `.dev.yml` (bind mounts, hot reload, mailpit), `.prod.yml` (replicas, resource limits, no source mounts). Containers: `web`, `console`, `api`, `worker`, `beat`, `postgres`, `redis`, `storage` (SeaweedFS, S3-compatible), `nginx`, (+ `prometheus`, `grafana`, `mailpit` in dev).
- CI (GitHub Actions): lint (ruff, eslint) → type check (mypy --strict, tsc) → unit → integration (PostgreSQL + Redis service containers) → build → docker build → security (pip-audit, pnpm audit, Trivy, gitleaks) → deploy staging. Production is gated by a GitHub Environment approval.

## 13. Repository layout (adjusted from the brief)

```
apps/
  web/            # public site + patient portal (React, Vite, prerender)
  console/        # admin, lab, collector, corporate, partner shells
packages/
  ui/             # design system (Tailwind + shadcn/ui based)
  api-client/     # generated TS client + TanStack Query hooks
  i18n/           # en/bn messages, formatters (৳, dates, bn digits)
  config/         # shared tsconfig/eslint/tailwind presets
services/
  api/            # FastAPI modular monolith
    app/core/     # config, db, security, rbac, errors, logging, outbox, storage
    app/modules/  # auth, patient, catalog, centre, scheduling, booking, …
    alembic/
    tests/
infrastructure/
  nginx/  postgres/  frontend/  prometheus/
docs/
scripts/          # seed, codegen, db helpers
docker-compose.yml  docker-compose.dev.yml  docker-compose.prod.yml
.env.example  README.md  LICENSE
```

The deviation from the brief's `services/*` per-service folders is deliberate (ADR-1). Each module folder is the future service boundary.

## 14. Future extensibility

- **Service extraction order** (when load or team size demands it): notification → report (PDF) → payment → search (OpenSearch) → analytics.
- **Search:** a `SearchBackend` interface. The PG implementation uses `tsvector` + `pg_trgm` + a synonym table; an OpenSearch implementation can drop in.
- **Instruments:** a `lab.instrument_results_inbox` table + an HL7/ASTM listener container later.
- **AI:** an isolated `ai` module behind feature flags. Outputs are stored with `generated_by_ai=true`, never auto-applied, and require staff confirmation.
- **Mobile apps:** same `/api/v1`; push via FCM device tokens.
