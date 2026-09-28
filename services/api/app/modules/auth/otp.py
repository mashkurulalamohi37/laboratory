"""One-time passwords stored (as HMAC digests) in Redis with TTL and attempt limits."""

from __future__ import annotations

import secrets
from enum import StrEnum

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import hit
from app.core.redis import get_redis
from app.core.security import hmac_digest
from app.modules.notification.sms import send_sms


class OtpPurpose(StrEnum):
    LOGIN = "LOGIN"
    RESET = "RESET"
    TWO_FACTOR = "TWO_FACTOR"


class OtpInvalid(AppError):
    status_code = 401
    code = "OTP_INVALID"
    message = "The code is incorrect or has expired."


class OtpAttemptsExceeded(AppError):
    status_code = 429
    code = "OTP_ATTEMPTS_EXCEEDED"
    message = "Too many incorrect attempts. Please request a new code."


_MESSAGES = {
    OtpPurpose.LOGIN: "{code} is your Nirnoy login code. It expires in {minutes} minutes. "
    "Never share this code.",
    OtpPurpose.RESET: "{code} is your Nirnoy password reset code. It expires in {minutes} minutes.",
    OtpPurpose.TWO_FACTOR: "{code} is your Nirnoy staff sign-in code. It expires in {minutes} "
    "minutes.",
}


def _key(purpose: OtpPurpose, subject: str) -> str:
    return f"otp:{purpose.value}:{subject}"


def _attempts_key(purpose: OtpPurpose, subject: str) -> str:
    return f"otp:attempts:{purpose.value}:{subject}"


def _generate(length: int) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


async def issue_otp(
    purpose: OtpPurpose, phone: str, *, ip: str | None, subject: str | None = None
) -> None:
    """Generate, store and send an OTP. `subject` defaults to the phone number; 2FA uses the
    challenge id so a code is bound to one login attempt."""
    s = get_settings()
    await _throttle(purpose, phone, ip)

    subject = subject or phone
    code = _generate(s.otp_length)
    redis = get_redis()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.set(
            _key(purpose, subject),
            hmac_digest(f"{purpose.value}:{subject}:{code}"),
            ex=s.otp_ttl_seconds,
        )
        pipe.delete(_attempts_key(purpose, subject))
        await pipe.execute()

    body = _MESSAGES[purpose].format(code=code, minutes=s.otp_ttl_seconds // 60)
    await send_sms(phone, body, category=f"otp_{purpose.value.lower()}")


async def verify_otp(purpose: OtpPurpose, subject: str, code: str) -> None:
    """Consume an OTP. Raises on mismatch, expiry or too many attempts."""
    s = get_settings()
    redis = get_redis()
    key, attempts_key = _key(purpose, subject), _attempts_key(purpose, subject)

    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, s.otp_ttl_seconds)
    if attempts > s.otp_max_attempts:
        await redis.delete(key)
        raise OtpAttemptsExceeded()

    expected = hmac_digest(f"{purpose.value}:{subject}:{code.strip()}")
    # Compare-and-delete atomically so a code can be consumed exactly once.
    consumed = await redis.eval(_CONSUME_LUA, 2, key, attempts_key, expected)  # type: ignore[misc]
    if int(consumed) != 1:
        raise OtpInvalid()


async def deliver_nothing(purpose: OtpPurpose, phone: str, *, ip: str | None) -> None:
    """Apply the same rate limits as `issue_otp` without sending, so responses and throttling
    are identical whether or not an account exists (prevents user enumeration)."""
    await _throttle(purpose, phone, ip)


async def _throttle(purpose: OtpPurpose, phone: str, ip: str | None) -> None:
    s = get_settings()
    await hit(
        f"otp-send:{purpose.value}:{phone}",
        limit=s.otp_send_limit_per_phone,
        window_seconds=s.otp_send_window_seconds,
    )
    if ip:
        await hit(
            f"otp-send-ip:{ip}",
            limit=s.otp_send_limit_per_ip,
            window_seconds=s.otp_send_window_seconds,
        )


_CONSUME_LUA = """
local v = redis.call('GET', KEYS[1])
if not v then return -1 end
if v == ARGV[1] then
  redis.call('DEL', KEYS[1], KEYS[2])
  return 1
end
return 0
"""
