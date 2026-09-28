# Environment variables

All configuration comes from environment variables (`services/api/app/core/config.py`).
`.env.example` lists every variable with development defaults. **Never commit `.env`.**
In staging and production, inject values from the platform's secret manager.

The API validates configuration at startup and **refuses to start** when:

- `JWT_SECRET` or `OTP_HMAC_SECRET` is shorter than 32 characters;
- in `staging`/`production`: a secret contains a placeholder marker (`change-me`, `dev-only`, …),
  `REFRESH_COOKIE_SECURE` is false, or `SMS_PROVIDER=console`.

Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## API / worker

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` · `test` · `staging` · `production` |
| `LOG_LEVEL` | `INFO` | JSON logs to stdout |
| `DATABASE_URL` | local | `postgresql+asyncpg://user:pass@host:5432/db` |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | 10 / 10 | Per process; use PgBouncer in production |
| `REDIS_URL` | `redis://localhost:6379/0` | Include the password in staging/production |
| `CELERY_BROKER_URL` | = `REDIS_URL` | Optional separate broker |
| `S3_ENDPOINT_URL` | local SeaweedFS | Unset for AWS S3 |
| `S3_SERVER_SIDE_ENCRYPTION` | `AES256` | Empty disables SSE (local emulator only) |
| `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_PREFIX` | | Buckets are `<prefix>-prescriptions`, `-reports`, `-invoices`, `-attachments`, `-cms-public` |
| `JWT_SECRET` | — (**required**) | HS256 signing key for access tokens |
| `ACCESS_TOKEN_TTL_SECONDS` | 900 | |
| `REFRESH_TOKEN_TTL_DAYS` | 30 | Session lifetime; refresh tokens rotate on every use |
| `REFRESH_COOKIE_SECURE` | `true` | `false` only for plain-http local development |
| `OTP_HMAC_SECRET` | — (**required**) | OTPs are stored as HMAC digests |
| `OTP_TTL_SECONDS`, `OTP_MAX_ATTEMPTS` | 300, 5 | |
| `OTP_SEND_LIMIT_PER_PHONE`, `OTP_SEND_LIMIT_PER_IP`, `OTP_SEND_WINDOW_SECONDS` | 3, 10, 900 | |
| `LOGIN_ATTEMPT_LIMIT`, `LOGIN_ATTEMPT_WINDOW_SECONDS` | 5, 900 | Per identifier; ×6 per IP |
| `STAFF_TWO_FACTOR_REQUIRED` | `true` | Staff sign in with password + SMS code |
| `SMS_PROVIDER` | `console` | `console` (dev/test only) · `disabled`. Real BD gateways are added behind the same interface |
| `CORS_ORIGINS` | Vite dev ports | JSON list. Not needed behind the same-origin gateway |
| `SENTRY_DSN` | — | Enables error tracking (PII scrubbing on) |
| `API_WORKERS` | 2 | Uvicorn workers (container) |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxies trusted for `X-Forwarded-For` |

## Seeding

| Variable | Notes |
|---|---|
| `SEED_SUPERADMIN_PHONE`, `SEED_SUPERADMIN_PASSWORD`, `SEED_SUPERADMIN_NAME`, `SEED_SUPERADMIN_EMAIL` | Bootstrap super admin; created only if none exists |
| `DEMO_STAFF_PASSWORD` | Password for `seed --demo` DEMO staff accounts (development/test only; refused elsewhere) |

## Docker Compose

| Variable | Notes |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database container |
| `REDIS_PASSWORD` | Empty in development; required in staging/production |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Also configure the local SeaweedFS `storage` container |
| `API_PORT` | Host port for the dev API (default 8000) |
| `WEB_HOST`, `CONSOLE_HOST`, `HTTP_PORT` | nginx gateway host routing |
| `IMAGE_TAG` | Image tag used by deploys (the git SHA) |

## Frontends (build time)

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | Empty = same origin (recommended; the gateway serves `/api`) |
| `API_PROXY_TARGET` | Vite dev proxy target (default `http://localhost:8000`) |
