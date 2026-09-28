# Deployment

## Topology (initial)

One Docker Compose host per environment, behind a TLS-terminating load balancer:

```
LB (TLS) → nginx (gateway: rate limits, routing, request IDs)
             ├─ /api/*   → api (uvicorn, N workers, replicas)
             ├─ web host → web (static SPA, nginx-unprivileged)
             └─ console  → console (static SPA)
           api/worker/beat → PostgreSQL, Redis, S3-compatible storage
```

For production, prefer managed PostgreSQL (automated backups + PITR), managed Redis and S3
over the bundled containers. The compose services then point at those endpoints via `.env`.

## Pipeline

1. **CI** (`.github/workflows/ci.yml`) on every PR and push: backend lint/types/boundaries,
   unit + integration tests, migration drift check, API contract check, frontend
   lint/types/tests/build, Playwright E2E against the docker stack, image builds with Trivy
   scans, secret scanning and dependency audits.
2. **Staging** deploys automatically from `main` after all jobs pass, once the repository
   variable `STAGING_DEPLOY_ENABLED=true` and the `staging` environment secrets
   (`STAGING_DEPLOY_HOST`, `STAGING_DEPLOY_SSH_KEY`) are configured.
3. **Production** is manual (`deploy-production.yml`, run with a SHA verified on staging) and
   gated by required reviewers on the `production` GitHub environment.

`scripts/deploy.sh` checks out the SHA on the host, builds images, runs migrations
(`migrate` service: `alembic upgrade head` + idempotent seed), then rolls the services.

## Migrations

- Every schema change is an Alembic migration reviewed in the PR; CI fails if models and
  migrations drift (`alembic check`).
- Use expand → migrate → contract for changes that must stay compatible with the running
  version (add nullable column → backfill → enforce/remove in a later release).

## Backups and recovery (targets: RPO ≤ 15 min, RTO ≤ 4 h)

- PostgreSQL: daily base backup + continuous WAL archiving (managed service PITR).
- Object storage: bucket versioning on `reports`, `prescriptions`, `invoices`.
- Restore drills each quarter; record the measured RTO.

## Health and observability

- `/health` (via gateway) · `/live` and `/ready` (internal only; `/ready` checks PostgreSQL and
  Redis, reports storage).
- `/metrics` is served to the internal network only (Prometheus scrape).
- JSON logs carry `request_id`; the same ID is returned in `X-Request-ID` and in error bodies.
