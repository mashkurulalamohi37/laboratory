# Audit Summary, Implementation Roadmap and Risks

## 1. Repository analysis

`d:\Intern Projects\Diagnostic` was **empty** at audit time (no code, no git history). This is a greenfield build with no compatibility constraints. The audit added only `docs/`.

## 2. Frontend architecture

- pnpm workspaces + Turborepo. TypeScript `strict: true`, `noUncheckedIndexedAccess`.
- **apps/web:** React 18 + Vite + React Router (data routers) + prerendering for public catalog routes. TanStack Query (API cache), React Hook Form + Zod, i18next (en/bn), lazy routes per section. Route groups: `/(public)`, `/account/*` (auth-guarded), `/book/*` (stepper), `/verify/:token`.
- **apps/console:** same stack as SPA only. Shells per persona (admin, lab, collector, corporate, partner). Nav and routes derive from `/me` permissions. Guarded routes plus server enforcement. TanStack Table + react-virtual for large tables. Recharts for analytics.
- **packages/api-client:** generated from OpenAPI (`openapi-typescript` + a thin fetch wrapper) → typed hooks. The wrapper handles the envelope, request IDs, a single-flight 401→refresh retry, and error normalisation into `ApiError{code}`.
- Testing: Vitest + React Testing Library (components/hooks), MSW for API mocks, Playwright E2E against the Docker stack.

## 3. Implementation phases

Each phase ends with the **quality gate** from the brief (build, migrations, containers up, docs, tests, lint/types, responsive states) and an implementation report.

| Phase | Scope | Exit demo |
|---|---|---|
| **1 Foundation** ✅ ([report](phase-reports/phase-1.md)) | Monorepo, Docker Compose (dev/prod), Nginx, PG, Redis, S3 storage, Celery; FastAPI core (config, logging, errors, request-id, DB/UoW, outbox, storage, health); Alembic baseline; auth (OTP, password, JWT, refresh rotation, sessions, 2FA for staff); RBAC + scopes + audit log; `packages/ui` foundations; web + console shells with login; CI pipeline | Log in as patient (OTP via console log/mailpit) and as admin; permission-gated admin page; `/docs` live; CI green |
| **2 Catalog** ✅ ([report](phase-reports/phase-2.md)) | Departments, categories, sample types, tests, parameters, reference ranges, packages, concerns, price lists, centres, geo master, search (FTS + trigram + synonyms), CMS basics (banners, pages, FAQs); public home, test list/detail, package list/detail, centre locator; SEO prerender + sitemap; seed data | Search "sugar" → FBS, HbA1c, diabetes package; SEO pages render without JS |
| **3 Booking and payment** ✅ ([report](phase-reports/phase-3.md)) | Patients, family, addresses, slots (templates → instances, holds), quote, booking state machine, coupons, payment abstraction + SSLCommerz sandbox + Cash (bKash/Nagad next, depending on credentials), notifications (SMS/email) v1; patient portal bookings | Full mobile booking with coupon and sandbox payment; concurrent slot test proves no overbooking |
| **4 Collection and samples** ✅ ([report](phase-reports/phase-4.md)) | Zones, collectors, auto-assign, collector mobile UI (offline queue), barcodes + label print, sample events, transfers, receiving, rejection + recollection | Collector completes an assignment; lab receives the barcoded batch |
| **5 Lab and results** ✅ ([report](phase-reports/phase-5.md)) | Lab orders, worklists, result entry, range engine + flags, critical alerts, verification (four-eyes), amendments | Tech enters → critical alert → pathologist verifies |
| **6 Reports** ✅ ([report](phase-reports/phase-6.md)) | PDF template (en/bn), async generation, versions, signatures, QR verification, signed downloads, shares, guest access; patient report portal | Patient downloads and verifies a report; amendment produces v2 |
| **7 Corporate, partner, billing** ✅ ([report](phase-reports/phase-7.md)) | Invoices, corporate roster/bulk booking/consent, partner portal, commission engine + ledger | Corporate monthly invoice; partner commission statement |
| **8 Inventory, finance, CRM, notifications** ✅ ([report](phase-reports/phase-8.md)) | Inventory ledger + alerts + POs, expenses/AR/AP, support tickets, full notification template management, in-app/push | Low-stock alert; ticket lifecycle |
| **9 Analytics and polish** ✅ ([report](phase-reports/phase-9.md)) | Aggregates + dashboard, health timeline + trends, search improvements, performance and load tests, a11y audit, docs set (deployment, admin guide, onboarding, troubleshooting) | Dashboard KPIs; k6 load test report |

**MVP cut:** phases 1–6 give the complete patient → report journey (acceptance criteria in the brief 1–21). Phases 7–9 cover the business/back-office breadth.

## 4. Risk list

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Scope is very large (about 13 products). A "build everything" push produces shallow code | High | Phase gates; MVP = phases 1–6; each phase shippable |
| R2 | Payment gateway credentials/merchant approval delays (bKash/Nagad need business onboarding) | High | Provider interface + SSLCommerz sandbox first; Cash path; adapters behind flags |
| R3 | Clinical safety: wrong reference-range match or flag | Critical | Specificity-ordered matcher with exhaustive unit tests; range snapshot stored with result; four-eyes verification; seed ranges labelled **DEMO — not for clinical use** until reviewed by a pathologist |
| R4 | Regulatory/privacy (BD data protection law evolving; DGHS lab licensing; report signature validity) | High | Consent model, audit, data minimisation; confirm signature approach and retention with legal (PRD §8) |
| R5 | SEO with a Vite SPA | Medium | Prerendering (ADR-4); Next.js fallback if needed |
| R6 | Bangla PDF rendering (conjuncts) | Medium | WeasyPrint + Noto Sans Bengali, verified in a Phase 1 spike |
| R7 | Collector connectivity | Medium | Offline action queue; idempotent transition endpoints with client timestamps |
| R8 | Slot overbooking under concurrency | Medium | Row locks + DB check constraint + concurrency test in CI |
| R9 | Modular-monolith boundaries erode over time | Medium | import-linter contracts in CI; schema-per-module; code review |
| R10 | SMS cost/abuse via OTP endpoints | Medium | Per-phone/IP limits, CAPTCHA after thresholds, cost alerts |
| R11 | Trademark/branding confusion with the reference | Medium | Original name/identity; no reference copy or assets; legal check of the final name |
| R12 | Windows dev environment (this machine) vs Linux containers | Low | Everything runs in Docker; `.gitattributes` enforces LF; scripts in POSIX sh + `make`-less npm scripts |

## 5. Decisions (resolved 2026-09-26: plan approved; defaults applied)

ADR-1, ADR-3 and ADR-4 approved. The working name stays a placeholder. SSLCommerz sandbox and cash come first (Phase 3). SMS sits behind a provider interface (dev console provider for now). One branch at launch, with a multi-branch-ready schema. Report signatures use a scanned signature plus the audit trail (Phase 6). Git is initialised locally, with no commits yet.

### Original questions

1. **Approve ADR-1** (modular monolith with extractable modules) instead of 20 deployable services from day one.
2. **Approve ADR-3** (two frontend apps: `web` + `console`) instead of three (web/admin/partner).
3. **Approve ADR-4** (Vite + prerender for SEO), or allow Next.js for the public web only.
4. Working brand name (placeholder "Nirnoy Diagnostics") — keep for now?
5. First payment gateway and SMS provider (PRD §8).
6. Initialise a git repository here? (Not done during the audit.)
