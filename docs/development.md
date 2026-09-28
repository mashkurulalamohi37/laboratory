# Development guide

Onboarding, conventions, testing and troubleshooting. Start with the [README](../README.md)
quick start.

## Backend conventions (`services/api`)

**Module layout.** Each bounded context lives in `app/modules/<name>/`:

| File | Responsibility |
|---|---|
| `api.py` | FastAPI router: HTTP ↔ schemas, permission dependencies, OpenAPI docs |
| `schemas.py` | Pydantic request/response models |
| `service.py` | Use-cases and business rules. **The only entry point other modules may call** |
| `repository.py` | SQLAlchemy queries |
| `models.py` | ORM tables, in the module's own PostgreSQL schema |
| `permissions.py`, `events.py`, `tasks.py` | as needed |

`app/core` holds cross-cutting infrastructure and must never import a module. Boundaries are
checked by `lint-imports` (contracts in `pyproject.toml`).

**Transactions.** `Depends(get_session)` opens one transaction per request: it commits when the
endpoint returns and rolls back on any exception. Therefore:

- raise an `AppError` subclass (`NotFound`, `Conflict`, `BusinessRuleViolation`, …) and the
  request's writes are discarded;
- run cache invalidation and other side effects with `on_commit(session, callback)` so they
  only happen after a successful commit;
- use `independent_transaction()` only for records that must persist even though the request
  fails (failed-login audit, token-reuse revocation).

**Authorization.** Guard routes with `Depends(require(P.SOMETHING))`. When a resource belongs to a
branch/lab/corporate/partner, also check `principal.require(perm, ScopeType.X, scope_id)` in the
service, or filter queries with `principal.scope_ids(...)`. Patients act on their own data
through ownership checks, not staff permissions.

**Auditing.** Call `audit.record(session, action=..., entity_type=..., entity_id=..., before=...,
after=...)` in the same transaction as the change. Sensitive keys are scrubbed automatically.

**Errors.** Never return raw exceptions. Error codes are part of the API contract; add new
ones as `AppError` subclasses with a stable `code`.

**Migrations.** Change models, then `alembic revision --autogenerate -m "..."`. Always read
the generated file: autogenerate misses things such as trigger functions and data backfills.

## Frontend conventions

- **Components** come from `@nirnoy/ui`. Add missing primitives there instead of styling
  one-off elements in apps.
- **Data** goes through TanStack Query with the typed client:
  `unwrap(api.GET("/api/v1/..."))`. The client attaches the access token, refreshes it
  silently, and throws `ApiError` (`code`, `requestId`, `fieldErrors()`).
- **Every data view** renders loading, empty, error (with retry and request ID) and content.
  `DataTable` does this for you.
- **Forms** use React Hook Form + Zod for instant feedback. Server validation errors are mapped
  back onto fields with `err.fieldErrors()`.
- **Text** goes through i18n (`useTranslation("<namespace>")`). Add keys to both `en` and `bn`;
  a unit test fails if the catalogs diverge.
- **Tokens** are held in memory only. The refresh token is an HttpOnly cookie scoped to
  `/api/v1/auth`. Never put credentials in `localStorage`.

## API contract workflow

1. Change the endpoint and Pydantic schemas in the API.
2. `pnpm api:openapi && pnpm api:types` regenerates `packages/api-client/openapi.json` and
   `src/schema.d.ts`.
3. Commit both. CI fails if they are stale.

## Testing

| Layer | Tool | Where | Needs |
|---|---|---|---|
| Backend unit | pytest | `services/api/tests/unit` | nothing |
| Backend integration | pytest + httpx | `services/api/tests/integration` | PostgreSQL + Redis (`TEST_DATABASE_URL`, `TEST_REDIS_URL`); skipped with a reason otherwise |
| Frontend unit/component | Vitest + Testing Library | `*.test.ts(x)` in packages and apps | nothing |
| End-to-end | Playwright | `e2e/tests` | running stack + Redis (reads dev SMS codes) |

Integration tests migrate a dedicated `nirnoy_test` database from scratch (schemas dropped
first) and truncate data between tests. Never point `TEST_DATABASE_URL` at a database you care
about.

## Troubleshooting

| Symptom | Fix |
|---|---|
| API exits with `JWT_SECRET must be set…` | Copy `.env.example` to `.env` (repo root). The API reads `../../.env` and `services/api/.env` |
| Login OTP never arrives in development | Codes are printed in API logs: `docker compose logs -f api` |
| `RATE_LIMITED` while testing OTP | Wait out the window, or clear Redis: `docker compose exec redis redis-cli FLUSHDB` |
| Signed out after every reload (web) | The refresh cookie must be same-origin: use the Vite proxy (`/api`), not `http://localhost:8000` directly, and set `REFRESH_COOKIE_SECURE=false` on plain http |
| Integration tests all skipped | PostgreSQL/Redis unreachable. Start the dev compose stack; the reason is printed with `pytest -rs` |
| `alembic check` reports drift | A model changed without a migration: autogenerate one and review it |
| `docker` commands hang on Windows | Restart Docker Desktop (tray icon → Restart). Check `wsl -l -v` shows `docker-desktop` running |
| API calls return `{"detail":"Not Found"}` without `X-Request-ID` | Another process owns port 8000 (for example another Docker container). Run the API elsewhere and set `API_PROXY_TARGET=http://127.0.0.1:<port>` for Vite. The proxy targets `127.0.0.1`, not `localhost`, so IPv6 listeners cannot intercept it |
| `/ready` reports Redis `fail` on Windows but Redis is up | Use `127.0.0.1` rather than `localhost` in URLs: a refused IPv6 (`::1`) connect costs about 2 s on Windows, which exceeds the readiness timeout |
| Turbo: "Unable to find package manager binary" | `corepack enable` (admin shell), or run tasks with `corepack pnpm -r run <task>` |
