"""Time helpers. Storage is always UTC; display and opening hours use Bangladesh time."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

#: Bangladesh Standard Time. Fixed UTC+6 (no daylight saving since 2009), so no tz database
#: is needed on hosts or slim images that lack one.
DHAKA_TZ = timezone(timedelta(hours=6), "Asia/Dhaka")


def utcnow() -> datetime:
    return datetime.now(UTC)


def dhaka_now() -> datetime:
    return datetime.now(DHAKA_TZ)
