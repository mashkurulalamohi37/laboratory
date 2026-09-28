# Phase 1 report: Foundation

**Date:** 2026-09-27 · **Scope:** infrastructure, backend and frontend foundations, authentication, RBAC, audit logging, CI/CD.

## Completed

- **Monorepo:** pnpm workspaces + Turborepo. Two apps (`web`, `console`), shared `ui`, `app-core`, `api-client`, `i18n`, `config` packages, and `e2e`.
- **API foundation (FastAPI modular monolith):**
  - typed settings that refuse insecure production config;
  - structured JSON logs with request IDs and secret redaction;
  - standard success/error envelopes, including unexpected 500s (never leak internals, always carry a request ID);
  - security headers;
  - one DB transaction per request, with after-commit hooks and independent transactions for must-persist security events;
  - Redis rate limiter, S3 storage adapter, transactional outbox with Celery relay, and Celery queues/beat;
  - Prometheus metrics, Sentry hook, `/health` `/live` `/ready`.
- **Authentication:**
  - patient sign-in and registration by SMS OTP (HMAC-stored, TTL, attempt limit, per-phone and per-IP send limits, no account enumeration);
  - password login (Argon2id, timing-uniform, per-identifier and per-IP limits), with mandatory SMS second factor for staff;
  - 15-minute JWT access tokens and rotating refresh tokens in an HttpOnly, SameSite=Strict, path-scoped cookie; body delivery for future mobile apps;
  - refresh-token reuse detection that revokes the session (a 30-second grace covers concurrent tabs);
  - immediate access-token revocation on logout or suspension;
  - device/session list and revoke, logout everywhere, password set/change/reset (reset signs out all sessions), profile and language preference.
- **RBAC:**
  - 52 permissions and 16 roles seeded, with role grants scoped to GLOBAL, BRANCH, LAB, CORPORATE or PARTNER;
  - server-side enforcement on every endpoint; principal cache invalidated on commit, so grant changes apply on the user's next request;
  - guard rails: only SUPER_ADMIN manages privileged roles; no self-demotion or self-disable; the last super admin is protected; SUPER_ADMIN permissions are immutable; only pathologists verify results; collectors and corporate admins get no clinical read access.
- **Audit:** append-only `audit.audit_logs` (UPDATE, DELETE and TRUNCATE are blocked by a trigger) records actor, roles, IP, user agent, request ID and before/after values, with sensitive keys scrubbed. There is a read-only search API and console page.
- **Database:** schemas `core`, `auth` and `audit`; baseline Alembic migration verified against PostgreSQL 16 (upgrade, `alembic check` with no drift, downgrade/upgrade round trip). Idempotent seed covers RBAC, a bootstrap super admin and DEMO staff (development only).
- **Frontend:**
  - design system (tokens for light/dark, Button, Field, inputs incl. phone/OTP/password, Card, Alert, Badge, Modal, Drawer, ConfirmDialog with type-to-confirm, DataTable with loading/empty/error states and mobile card layout, Pagination, states);
  - English/Bangla catalogs with a parity test; ৳, Bangla-digit, phone and date formatters;
  - typed API client generated from OpenAPI, with in-memory tokens and single-flight silent refresh.
  - **Web:** home, OTP/password sign-in, account (profile, password, devices), 404 and error boundary.
  - **Console:** staff sign-in with 2FA; permission-filtered shell; dashboard; Users (search, filters in the URL, pagination, create staff, status change with reason and confirmation, grant/revoke roles); Roles (permission editor); Audit log (filters, before/after detail).
- **Infrastructure:**
  - Dockerfiles (non-root API; unprivileged nginx for the SPAs with CSP and immutable asset caching);
  - `docker-compose.yml` / `.dev.yml` / `.prod.yml`;
  - nginx gateway with auth and API rate-limit zones, request IDs, and internal endpoints blocked;
  - S3 bucket bootstrap (`app.scripts.init_storage`: private buckets plus one public CMS bucket; works on any S3 provider), local SeaweedFS storage service, Prometheus config, `.env.example`.
- **CI/CD:**
  - GitHub Actions: backend lint/format/strict types/module boundaries/tests/migration drift; API-contract drift check; frontend lint/types/tests/build; Playwright E2E on the docker stack; image builds with Trivy; gitleaks, pip-audit and pnpm audit;
  - staging auto-deploy (opt-in via variable), and production as a manual, approval-gated workflow.

## Changed files (key)

`services/api/app/core/*` · `services/api/app/modules/{auth,audit,notification,system}/*` · `services/api/alembic/versions/0001_baseline.py` · `services/api/app/scripts/{seed,export_openapi}.py` · `packages/*` · `apps/{web,console}/src/*` · `e2e/*` · `docker-compose*.yml` · `infrastructure/*` · `.github/workflows/*` · `docs/{development.md,deployment/*}` · `README.md`

## Database

| Revision | Content |
|---|---|
| `0001` | Schemas `core`/`auth`/`audit`; `pg_trgm`; `core.outbox_events`; `auth.users`, `roles`, `permissions`, `role_permissions`, `user_roles` (scoped, NULLS NOT DISTINCT unique), `sessions`, `refresh_tokens`; `audit.audit_logs` + immutability triggers |

## APIs

`POST /api/v1/auth/{send-otp, verify-otp, login, 2fa/verify, refresh, logout, logout-all, logout-cookie, password/forgot, password/reset, password/change}` · `GET|DELETE /api/v1/auth/sessions[/{id}]` · `GET|PATCH /api/v1/me` · `GET|POST /api/v1/admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}/status`, `POST|DELETE /admin/users/{id}/roles[/{user_role_id}]` · `GET /admin/roles`, `PUT /admin/roles/{code}/permissions`, `GET /admin/permissions` · `GET /admin/audit-logs` · `/health` `/live` `/ready` `/metrics`. Interactive docs: `/api/docs`.

## Tests

| Suite | Result |
|---|---|
| Backend unit (pytest) | **41 passed** |
| Backend integration against PostgreSQL 16.6 (pytest + httpx) | **29 passed**. Covers OTP single use, attempt limits and rate limits; refresh rotation, reuse revocation and grace; logout/suspension revocation; staff 2FA; RBAC denials; immediate grant effect; privileged-role and last-super-admin protection; audit immutability |
| Migration drift (`alembic check`) and downgrade/upgrade round trip | **clean** |
| ruff · ruff format · mypy --strict · import-linter (3 contracts) | **clean** |
| Frontend unit/component (Vitest) | **43 passed** (i18n 16, api-client 6, ui 6, app-core 8, web 3, console 4) |
| ESLint (incl. jsx-a11y) · tsc strict · production builds | **clean** |
| E2E (Playwright: mobile patient OTP journey + Bangla; desktop staff 2FA, user admin, audit, permission denial) | **4 passed** against a live API and dev servers |

**Docker verification (2026-09-27):** after Docker Desktop was restarted, the dev stack (`docker-compose.yml` + `docker-compose.dev.yml`) was built and started. All services reached healthy: postgres, redis, storage, api, worker, beat, mailpit; `migrate` exited 0 after migrations, bucket bootstrap and seed. `/ready` reports postgres, redis and storage `ok`, and the worker executes the beat-scheduled outbox relay. The 70 backend tests passed against the containerised **PostgreSQL 16 and Redis 7.4**, and the 4 E2E tests passed against the containerised API. Earlier runs used a portable PostgreSQL and a fakeredis stand-in while Docker was down.

**Not yet executed:** the production image builds (`runtime` API target, web and console images), the `fullstack` profile behind nginx, and the GitHub Actions workflows. They were skipped because the C: drive (where Docker stores images) was down to about 275 MB.

Bugs found and fixed by this verification:
- *Application:* a stale identity-map reload after role grants (`MissingGreenlet`); unexpected 500s losing their request ID; the seed and dev SMS output crashing on Windows consoles (non-ASCII); seed inputs not read from `.env` outside Docker; model index names drifting from the migration; LIKE wildcards not escaped in user search.
- *Docker setup:*
  - The MinIO images are no longer published, so local storage is now SeaweedFS (S3-compatible), with buckets created by `app.scripts.init_storage` (boto3, so it works with any S3 provider).
  - The worker and beat services now have `build` sections instead of trying to pull a local image.
  - The Redis password logic was expanded by Compose instead of the container shell (now escaped).
  - Inline comments in `.env` broke parsing (moved to their own lines).
  - Mailpit's SMTP host port clashed on Windows (now internal only).
  - The dev API host port is configurable (`API_PORT`) because 8000 was taken.

## Known issues / open items

1. **Production images and CI not yet exercised.** The `runtime` API image, the web and console images, the nginx `fullstack` profile and the GitHub workflows still need a first run (on GitHub, or locally once C: has a few GB free).
2. **Main bundle size.** Patient web first load is about 30 kB gzipped app code plus a 103 kB framework chunk (React, React Router). Phase 2 prerendering of public pages is the main LCP lever.
3. **SMS gateway.** Only the development `console` provider exists. A real Bangladesh gateway adapter is needed before any non-dev deployment (config blocks `console` outside development/test).
4. **JWT signing is HS256** (single issuer and verifier). The move to EdDSA/JWKS is documented for when services are extracted.
5. **Scope IDs are not yet validated** against branches, labs, corporates or partners; those tables arrive in Phases 2 and 7.
6. **Bangla copy** needs review by a native content editor.
7. **Brand name, logo and LICENSE** are placeholders or pending (no LICENSE file added; that is your decision).
8. The DEMO staff seed uses numbers in the `01900000xxx` range. They are only ever "sent" through the development console provider, but they are syntactically real BD numbers.

## Next phase (Phase 2: Catalog)

Departments, categories, sample types, tests and parameters with configurable reference ranges; packages; health concerns with synonyms (Bangla terms, "sugar" → glucose); branch price lists; centres and BD geo master data; PostgreSQL full-text + trigram search with autocomplete; CMS basics (banners, pages, FAQs); public home, test and package listing/detail, and centre locator pages with SEO prerendering and a sitemap; realistic seed data labelled DEMO.
