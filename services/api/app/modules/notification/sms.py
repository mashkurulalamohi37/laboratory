"""SMS provider abstraction.

Phase 1 ships the `console` provider for development/test only (config validation
forbids it in staging/production). Real BD gateways plug in behind `SmsProvider`.
"""

from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.phone import mask_phone
from app.core.redis import get_redis

#: Redis list per phone holding recent dev/test SMS bodies (newest first).
DEV_SMS_KEY_PREFIX = "dev-sms:"

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SmsMessage:
    to: str
    body: str
    category: str  # e.g. "otp", "booking" — used for metrics/routing, never contains PII


class SmsProvider(Protocol):
    code: str

    async def send(self, message: SmsMessage) -> str:
        """Send and return the provider message id."""
        ...


class ConsoleSmsProvider:
    """Development-only: prints to stdout (outside the structured log pipeline) and keeps
    the last messages in memory so tests can read OTPs."""

    code = "console"

    def __init__(self) -> None:
        self.outbox: deque[SmsMessage] = deque(maxlen=200)

    async def send(self, message: SmsMessage) -> str:
        self.outbox.append(message)
        if get_settings().environment == "development":
            sys.stdout.write(f"[DEV SMS -> {message.to}] {message.body}\n")
            sys.stdout.flush()
        # Readable by E2E tests (Playwright); this provider never runs outside dev/test.
        key = f"{DEV_SMS_KEY_PREFIX}{message.to}"
        async with get_redis().pipeline(transaction=True) as pipe:
            pipe.lpush(key, message.body)
            pipe.ltrim(key, 0, 9)
            pipe.expire(key, 600)
            await pipe.execute()
        return f"console-{len(self.outbox)}"

    def last_to(self, phone: str) -> SmsMessage | None:
        return next((m for m in reversed(self.outbox) if m.to == phone), None)


class DisabledSmsProvider:
    code = "disabled"

    async def send(self, message: SmsMessage) -> str:
        log.warning("sms_disabled", to=mask_phone(message.to), category=message.category)
        return "disabled"


_provider: SmsProvider | None = None


def get_sms_provider() -> SmsProvider:
    global _provider
    if _provider is None:
        name = get_settings().sms_provider
        _provider = ConsoleSmsProvider() if name == "console" else DisabledSmsProvider()
    return _provider


async def send_sms(to: str, body: str, *, category: str) -> str:
    provider = get_sms_provider()
    message_id = await provider.send(SmsMessage(to=to, body=body, category=category))
    log.info("sms_sent", to=mask_phone(to), category=category, provider=provider.code)
    return message_id
