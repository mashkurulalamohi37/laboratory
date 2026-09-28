# Nirnoy Laboratory & Diagnostic Platform

[![Build & Typecheck](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Backend](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)]()
[![Frontend](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)]()
[![Database](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)]()
[![Cache](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)]()
[![Architecture](https://img.shields.io/badge/Architecture-Modular_Monolith-blueviolet.svg)]()
[![Compliance](https://img.shields.io/badge/Compliance-ISO_15189_Ready-orange.svg)]()

> **Nirnoy** (নির্ণয় — *diagnosis*) is an enterprise-grade diagnostic laboratory and pathology platform designed specifically for the healthcare ecosystem in Bangladesh. It bridges public patient booking, home phlebotomy dispatch, cold-chain logistics, multi-department laboratory worksheets, automated analyzer ingestion, dual-step medical verification with digital signatures, and back-office operations (billing, corporate health, inventory, financial reconciliation, and CRM).

---

## 📑 Table of Contents

- [Architectural Overview](#-architectural-overview)
- [System Capabilities & Modules](#-system-capabilities--modules)
  - [1. Patient Web Portal (`apps/web`)](#1-patient-web-portal-appsweb)
  - [2. Staff & Laboratory Console (`apps/console`)](#2-staff--laboratory-console-appsconsole)
  - [3. Core Backend Services (`services/api`)](#3-core-backend-services-servicesapi)
- [Monorepo Structure](#-monorepo-structure)
- [Technology Stack](#-technology-stack)
- [Local Quick Start](#-local-quick-start)
  - [Prerequisites](#prerequisites)
  - [1. Clone and Configure Environment](#1-clone-and-configure-environment)
  - [2. Start Infrastructure & Database](#2-start-infrastructure--database)
  - [3. Run Migrations & Seed Data](#3-run-migrations--seed-data)
  - [4. Launch Backend API](#4-launch-backend-api)
  - [5. Launch Web and Console Applications](#5-launch-web-and-console-applications)
- [Pre-Seeded Demo Credentials](#-pre-seeded-demo-credentials)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Security & Compliance Principles](#-security--compliance-principles)
- [License](#-license)

---

## 🏛 Architectural Overview

```
                                      ┌────────────────────────────────────────┐
                                      │             Client Tier                │
                                      │  React 19 + Vite + Tailwind v4 + Radix │
                                      └───────────────────┬────────────────────┘
                                                          │
                              ┌───────────────────────────┴───────────────────────────┐
                              ▼                                                       ▼
                ┌───────────────────────────┐                           ┌───────────────────────────┐
                │   Patient Web Portal      │                           │  Staff & Lab Console      │
                │      (:5173 / web)        │                           │     (:5174 / console)     │
                └─────────────┬─────────────┘                           └─────────────┬─────────────┘
                              │                                                       │
                              └───────────────────────────┬───────────────────────────┘
                                                          │ Reverse Proxy / API Gateway
                                                          ▼
                                      ┌────────────────────────────────────────┐
                                      │         FastAPI Modular Monolith       │
                                      │           (:8000 /services/api)        │
                                      └───────────────────┬────────────────────┘
                                                          │
          ┌───────────────────────┬───────────────────────┼───────────────────────┬───────────────────────┐
          ▼                       ▼                       ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Auth & RBAC    │    │ Catalog & Search │    │ Booking & Slots  │    │  Sample Logistics│    │ Lab & Analyzers  │
│ (JWT + HttpOnly) │    │(pg_trgm + Syn)   │    │(Concurrency Lock)│    │(Barcode/ColdChn) │    │(Delta/Critical)  │
└──────────────────┘    └──────────────────┘    └──────────────────┘    └──────────────────┘    └──────────────────┘
          │                       │                       │                       │                       │
          ▼                       ▼                       ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Verified Reports │    │ Billing & Corp   │    │ Inventory & LOT  │    │ Finance & Recon  │    │ CRM & Escalation │
│ (Signed PDF + QR)│    │(SSLCommerz/B2B)  │    │(Reagents / POs)  │    │(Gateways/Ledger) │    │(SLA Tickets/SMS) │
└──────────────────┴────┴──────────────────┴────┴──────────────────┴────┴──────────────────┴────┴──────────────────┘
                                                          │
                                      ┌───────────────────┴────────────────────┐
                                      ▼                                        ▼
                      ┌───────────────────────────────┐        ┌───────────────────────────────┐
                      │    PostgreSQL 16 Engine       │        │         Redis 7 Cache         │
                      │  (Multi-schema, 78+ Tables,   │        │   (Slot Holds, Rate Limits,   │
                      │   Trigram Indexing, Audit)    │        │    Session Store, Pub/Sub)    │
                      └───────────────────────────────┘        └───────────────────────────────┘
```

---

## ⚡ System Capabilities & Modules

### 1. Patient Web Portal (`apps/web`)
- **Smart Catalog Search:** Real-time search across 34+ lab tests and 10 health packages with typo-tolerance (`pg_trgm`) and English/Bangla synonyms (e.g., searching *"sugar"* maps to *Fasting Blood Glucose*).
- **Home Collection & Centre Scheduling:** Step-by-step 5-stage checkout wizard with real-time address validation, district coverage checking, and concurrency-safe slot reservations.
- **Family Member Management:** Single-account tracking for dependents, elderly parents, and spouses with individual medical histories.
- **Health Trend & Timeline (`/account/health-timeline`):** Visual historical tracking of biomarkers (HbA1c, Cholesterol, Creatinine) over time.
- **Secure Online Payments:** Integrated SSLCommerz gateway sandbox (bKash, Nagad, cards) and Cash-on-Collection payment options.
- **Digital Report Vault:** Real-time download of cryptographically signed PDF medical reports.

### 2. Staff & Laboratory Console (`apps/console`)
- **Executive Operations Dashboard:** Real-time TAT (Turnaround Time) monitoring, pending sample backlogs, analyzer queues, and daily revenue metrics.
- **Accessioning & Barcoding:** High-speed barcode scanning, tube color verification (EDTA, Serum, Heparin), rejection reasons with sample re-draw workflows.
- **Phlebotomist Dispatch & Logistics:** Route assignment, GPS checkpoint logging, sample temperature monitoring (cold-chain compliance: 2°C–8°C).
- **Laboratory Worksheets & Result Entry:** Dual-step result entry with automated delta checks against patient historical values and instant critical-value alerts.
- **Pathologist Verification & Digital Signing:** Review, approve, or request rerun with doctor notes and automated public-verifiable QR code stamp generation.
- **Reagent & Inventory Tracking (`/inventory`):** LOT number tracking, expiry warnings, automated consumption deduction upon test validation, and purchase order lifecycles.
- **Financial Reconciliation (`/finance`):** MFS & bank statement reconciliation against SSLCommerz settlements, refund audit logs, and transaction ledgers.
- **Customer Support & CRM (`/crm`):** Ticket triage, complaint categorization, priority SLAs, internal activity logging, and SMS notification dispatch.

### 3. Core Backend Services (`services/api`)
- **Modular Monolith Architecture:** Decoupled business modules with isolated models, services, schemas, and endpoints.
- **Strict Role-Based Access Control (RBAC):** 53 fine-grained permissions across 16 predefined roles, with optional branch, lab, corporate, or partner scoping.
- **Immutable Financial Math:** All currency calculations stored as integer poisha (1 BDT = 100 poisha) preventing IEEE-754 floating-point drift.
- **Append-Only Auditing:** Tamper-proof audit log table capturing actor ID, IP address, timestamp, pre/post state JSON diffs on sensitive medical and financial entities.
- **Public Verification Service:** Anyone scanning a report QR code can verify its authenticity and authenticity hash on `GET /api/v1/reports/verify/{token}` without exposing unauthorized patient PII.

---

## 📂 Monorepo Structure

```
nirnoy-platform/
├── apps/
│   ├── web/                    # Patient-facing portal (React 19, Vite, Tailwind v4)
│   └── console/                # Staff, Doctor & Lab Operations app (React 19, Vite)
├── packages/
│   ├── ui/                     # Shared UI components (Tailwind v4, Radix, Lucide)
│   ├── app-core/               # Shared session management, auth guards, interceptors
│   ├── api-client/             # Type-safe API client generated from OpenAPI spec
│   ├── i18n/                   # Bilingual dictionary (English & Bengali), formatting
│   └── config/                 # Monorepo TypeScript & ESLint shared configurations
├── services/
│   └── api/                    # FastAPI backend service (Python 3.12, SQLAlchemy, Alembic)
│       ├── alembic/            # Database migration scripts (0001 through 0006)
│       └── app/
│           ├── core/           # Security, DB engines, Redis, config, exceptions
│           ├── modules/        # Domain modules (auth, catalog, booking, lab, report...)
│           └── scripts/        # Database seeders (RBAC, geography, catalog, DEMO data)
├── infrastructure/             # Gateway configurations (Nginx reverse proxy, prometheus)
├── docs/                       # Specifications, ERDs, phase completion reports (1-9)
├── docker-compose.yml          # Core containers (PostgreSQL 16, Redis 7, SeaweedFS)
├── docker-compose.dev.yml      # Development overrides and seed runners
├── turbo.json                  # Turborepo task pipelines
└── package.json                # Monorepo root definition
```

---

## 💻 Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend Frameworks** | React 19, TypeScript 5.8, Vite 6, React Router DOM 7 |
| **Styling & Components** | TailwindCSS v4, Radix UI Primitives, Lucide Icons, clsx, tailwind-merge |
| **State & Data Fetching** | TanStack React Query v5, Zustand, React Hook Form, Zod |
| **Backend Framework** | FastAPI 0.115+, Python 3.12, Uvicorn, Pydantic v2 |
| **Database & ORM** | PostgreSQL 16 (pg_trgm extension), SQLAlchemy 2.0 (asyncpg), Alembic |
| **Caching & Queues** | Redis 7, Redis Pub/Sub, Redis Slot-Locks |
| **Monorepo Tooling** | Turborepo, pnpm Workspaces |
| **Infrastructure** | Docker, Nginx, SeaweedFS (S3-compatible storage), Prometheus |

---

## 🚀 Local Quick Start

### Prerequisites
- [Node.js](https://nodejs.org/) `>= 20.0.0`
- [pnpm](https://pnpm.io/) `>= 9.0.0` (`corepack enable && corepack prepare pnpm@latest --activate`)
- [Python](https://www.python.org/) `>= 3.12`
- [Docker Desktop](https://www.docker.com/)

---

### 1. Clone and Configure Environment

```bash
git clone https://github.com/mashkurulalamohi37/laboratory.git
cd laboratory

# Copy default environment variables
cp .env.example .env
```

---

### 2. Start Infrastructure & Database

Spin up PostgreSQL 16, Redis 7, and SeaweedFS object storage:

```bash
docker compose up -d postgres redis s3
```

---

### 3. Run Migrations & Seed Data

Set up your Python virtual environment and run the database migrations and seed scripts:

```bash
cd services/api

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Apply all Alembic migrations (up to 0006)
alembic upgrade head

# Seed permissions, roles, BD geography, catalog, and demo staff accounts
python -m app.scripts.seed --demo

cd ../..
```

---

### 4. Launch Backend API

```bash
cd services/api
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API is live at: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/api/docs`
- Health check: `http://127.0.0.1:8000/health`

---

### 5. Launch Web and Console Applications

In a separate terminal, install monorepo dependencies and launch the dev servers:

```bash
# Install all node packages across workspaces
pnpm install

# Start both web (:5173) and console (:5174) in parallel
pnpm dev
```

- **Patient Web Application:** `http://localhost:5173`
- **Staff Operations Console:** `http://localhost:5174`

---

## 🔑 Pre-Seeded Demo Credentials

### Staff & Doctor Accounts (`http://localhost:5174`)

Password for all DEMO staff: **`Demo-Staff-2026`**

| Role | Mobile Phone | Scope / Accessible Modules |
| :--- | :--- | :--- |
| **Super Admin** | `01700000000` | Full global access *(Password: `change-me-Admin-2026`)* |
| **Administrator** | `01900000001` | System configuration, staff management, audit logs |
| **Lab Manager** | `01900000002` | Lab test quality control, analyzers, departments |
| **Pathologist** | `01900000003` | Worksheet approval, critical value sign-offs, notes |
| **Lab Technician** | `01900000004` | Worksheets, result entry, rerun flagging |
| **Phlebotomist / Collector** | `01900000005` | Home collection routes, cold-chain checkpoints |
| **Receptionist** | `01900000006` | In-person walk-ins, cash counter payments |
| **Accountant** | `01900000007` | Invoices, refund reconciliations (`/finance`) |
| **Inventory Manager** | `01900000010` | Reagent stock, purchase orders (`/inventory`) |
| **Customer Support** | `01900000008` | Support tickets, SLA escalation CRM (`/crm`) |
| **Content Manager** | `01900000009` | Health guides, test descriptions, promotion banners |

*(Note: In local development mode with `SMS_PROVIDER=console`, OTP 2FA codes are printed directly to the API terminal log).*

### Patient Account (`http://localhost:5173`)
- Enter any valid 11-digit Bangladeshi mobile number (e.g., `01712345678`).
- The 6-digit OTP code will be output to the API console.

---

## 🧪 Testing & Quality Assurance

```bash
# Run Turborepo checks across all frontends
pnpm lint
pnpm typecheck
pnpm build

# Run backend Python tests and code style checks
cd services/api
pytest -v
ruff check .
mypy app

# Run Playwright End-to-End browser suite
cd ../..
pnpm --filter @nirnoy/e2e e2e
```

---

## 🛡️ Security & Compliance Principles

- **Zero Client-Side Trust:** All authorization decisions are strictly enforced on the server via `services/api/app/modules/auth/permissions.py`. UI permission checks only control visual affordances.
- **HttpOnly Session Cookies:** Session refresh tokens (`nirnoy_rt`) are stored strictly in `HttpOnly, SameSite=Lax` cookies, preventing XSS access.
- **Immutable Financial Values:** Stored as integer poisha; price snapshot taken at the instant of order confirmation cannot be mutated by later catalog price modifications.
- **ISO 15189 Lab Standards:** Full audit logging on sample rejections, test result revisions, delta check deviations, and pathologist sign-off timestamps.
- **Strict Data Isolation:** Corporate and partner accounts are cryptographically partitioned by scoping rules in SQLAlchemy query filters.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
