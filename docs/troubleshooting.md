# Diagnostic Platform Troubleshooting & Incident Guide

## 1. Fast Diagnostics Checklist

When an unexpected incident occurs, check the following endpoints and logs:

```bash
# 1. API Health & Database Readiness
curl -s http://localhost:8000/health | jq .

# 2. Inspect active request error traces with Request ID
grep "req_01J8X..." /var/log/nirnoy/api.log

# 3. Redis connection and memory usage
redis-cli ping
redis-cli info memory
```

---

## 2. Common Scenarios & Resolutions

### A. Database Connection Pool Exhaustion
- **Symptom:** `asyncpg.exceptions.TooManyConnectionsError` or slow request timeouts.
- **Root Cause:** Excessive parallel worker processes or unclosed sessions.
- **Resolution:**
  1. Inspect PostgreSQL active connections: `SELECT count(*), state FROM pg_stat_activity GROUP BY state;`.
  2. Ensure `DATABASE_POOL_SIZE` is tuned to `10-20` per Uvicorn worker process.
  3. Validate that all FastAPI endpoints inject `session: Annotated[AsyncSession, Depends(get_session)]` without manual open loops.

---

### B. Barcode Accession Collision (409 Conflict)
- **Symptom:** Phlebotomist scanner raises `409 Conflict: Barcode already assigned`.
- **Root Cause:** Reused barcode label or dual collection attempt.
- **Resolution:**
  1. Inspect sample repository: `SELECT * FROM sample.samples WHERE barcode = 'BARCODE_VALUE';`.
  2. If the barcode was printed for a cancelled order, discard and scan a fresh vacutainer label.
  3. All specimen accessioning is strictly idempotent via `Idempotency-Key` headers.

---

### C. SMS Gateway / OTP Delivery Degradation
- **Symptom:** Patients report SMS verification codes are delayed.
- **Root Cause:** Local telecommunications gateway latency (e.g. Grameenphone / Robi bulk SMS route slowdown).
- **Resolution:**
  1. Check Redis key queue: `redis-cli llen dev-sms:*` or monitor gateway HTTP responses.
  2. Verify Celery notification worker status: `celery -A app.core.celery inspect ping`.
  3. Failover gateway routes in `app/modules/notification/sms.py` to secondary MFS/telecom SMS provider.

---

### D. PDF Report Generation Failure
- **Symptom:** Report shows `FAILED` during pathologist digital release.
- **Root Cause:** Object storage (SeaweedFS / AWS S3) unreachable or bucket permissions denied.
- **Resolution:**
  1. Verify S3 endpoint connectivity: `curl -I $S3_ENDPOINT_URL`.
  2. Check IAM access permissions for `s3:PutObject` on bucket `nirnoy-prod-reports`.
  3. Retry report compilation via Console: `/reports/{id}` -> "Re-sign & Release".

---

### E. Idempotency Key Replay (422 Unprocessable)
- **Symptom:** `Idempotency-Key` conflict when submitting duplicate bookings or payments.
- **Resolution:**
  1. Ensure client creates a distinct UUID v7 for each distinct intent.
  2. Replaying the identical key with the exact same payload returns the cached response safely.
