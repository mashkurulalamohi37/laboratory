"""Shared test configuration.

Unit tests need nothing external. Integration tests (marked `integration`) need PostgreSQL
and Redis, from TEST_DATABASE_URL / TEST_REDIS_URL (defaults match docker-compose.dev.yml),
and are skipped with a clear reason when those are unreachable.
"""

from __future__ import annotations

import os

# Settings are read at import time, so the test environment is fixed before any app import.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-enough-entropy-0123456789")
os.environ.setdefault("OTP_HMAC_SECRET", "test-otp-secret-with-enough-entropy-0123456789")
os.environ.setdefault("SMS_PROVIDER", "console")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ["REFRESH_COOKIE_SECURE"] = "false"  # the test client speaks plain http
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://nirnoy:nirnoy@localhost:5432/nirnoy_test"
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
