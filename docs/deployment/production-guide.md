# Production Deployment & Architecture Guide

## 1. System Architecture Overview

The Nirnoy Diagnostic Platform is engineered as a **high-reliability modular monolith** optimized for medical diagnostics operations in Bangladesh.

```
                      +-----------------------------+
                      |   Cloudflare / Edge CDN     |
                      +--------------+--------------+
                                     | (TLS 1.3, DDoS protection)
                                     v
                      +-----------------------------+
                      |    Nginx Reverse Proxy      |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              |                                             |
              v                                             v
  +-----------------------+                     +-----------------------+
  |  Web App (Patient)    |                     |  Console App (Staff)  |
  |  Port: 3000 (SPA)     |                     |  Port: 3001 (SPA)     |
  +-----------------------+                     +-----------------------+
              |                                             |
              +----------------------+----------------------+
                                     | /api/v1/*
                                     v
                      +-----------------------------+
                      |   FastAPI Modular Monolith  |
                      |   (Uvicorn 4x Workers)      |
                      +--------------+--------------+
                                     |
        +--------------------+-------+--------+--------------------+
        |                    |                |                    |
        v                    v                v                    v
+---------------+    +---------------+  +---------------+  +---------------+
| PostgreSQL 16 |    |    Redis 7    |  | S3/SeaweedFS  |  | Celery Workers|
| (11 Schemas)  |    | (Cache/Queue) |  | (PDF Reports) |  | (SMS/Async)   |
+---------------+    +---------------+  +---------------+  +---------------+
```

---

## 2. Infrastructure Prerequisites

| Component | Minimum Specification | Recommended Production Spec |
| :--- | :--- | :--- |
| **Compute (API & Workers)** | 2 vCPU, 4 GB RAM | 4 vCPU, 8 GB RAM (High-Compute) |
| **Database (PostgreSQL 16)** | 2 vCPU, 4 GB RAM, 50 GB SSD | 4 vCPU, 16 GB RAM, High-IOPS NVMe |
| **Cache (Redis 7)** | 1 vCPU, 1 GB RAM | 2 vCPU, 4 GB RAM (AOF Persistence) |
| **Object Storage** | S3-compatible, 50 GB | AWS S3 / SeaweedFS Distributed |

---

## 3. Database Migration Execution

All migrations run against the transactional multi-schema architecture (`auth`, `catalog`, `centre`, `booking`, `sample`, `lab`, `result`, `report`, `billing`, `inventory`, `finance`, `crm`, `notification`):

```bash
cd services/api
# Ensure virtualenv is active
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Execute zero-downtime database migration
alembic upgrade head
```

---

## 4. Environment Variables Configuration

| Variable | Description | Production Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Target environment | `production` |
| `DATABASE_URL` | AsyncPG connection string | `postgresql+asyncpg://user:pass@db-cluster:5432/nirnoy` |
| `REDIS_URL` | Redis cache and session broker | `redis://:pass@redis-cluster:6379/0` |
| `JWT_SECRET` | 64-character cryptographic token secret | *High-entropy random hex* |
| `OTP_HMAC_SECRET` | Secret key for verification tokens | *Cryptographic 64-char key* |
| `S3_ENDPOINT_URL` | Object storage gateway URL | `https://s3.ap-southeast-1.amazonaws.com` |
| `S3_BUCKET_PREFIX` | S3 bucket namespace | `nirnoy-prod` |
| `SENTRY_DSN` | Exception tracking endpoint | `https://...@sentry.io/...` |

---

## 5. Background Asynchronous Workers

Launch Celery background workers for email/SMS dispatch, invoice batch reconciliation, and PDF signing:

```bash
# General queue worker
celery -A app.core.celery worker -Q default,notifications,reports -c 4 --loglevel=INFO

# Celery beat scheduler (daily reconciliation and SLA monitors)
celery -A app.core.celery beat --loglevel=INFO
```

---

## 6. Zero-Downtime Deployment Sequence

1. **Pre-flight Check:** Verify DB health, redis connectivity, and S3 credentials via `GET /health`.
2. **Database Migration:** Run `alembic upgrade head` (all migrations are backwards-compatible).
3. **Rolling API Update:** Graceful restart of Uvicorn workers (`systemctl reload nirnoy-api`).
4. **Static Assets Release:** Invalidate edge CDN cache for patient web and console bundles.
5. **Post-deployment Verification:** Validate Prometheus `/metrics` and error rates.
